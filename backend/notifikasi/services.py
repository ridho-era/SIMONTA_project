from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from accounts.models import Role

from .models import Notifikasi, PengaturanNotifikasi, PengingatTerjadwal


OFFSET_FIELD = {7: "h_minus_7", 3: "h_minus_3", 1: "h_minus_1"}
JENIS_DOKUMEN = {Notifikasi.Jenis.DOKUMEN_BARU, Notifikasi.Jenis.REVIEW_TERBIT}
JENIS_JADWAL = {
    Notifikasi.Jenis.JADWAL_DISETUJUI,
    Notifikasi.Jenis.JADWAL_DITOLAK,
    Notifikasi.Jenis.JADWAL_DIBATALKAN,
    Notifikasi.Jenis.JADWAL_DIUSULKAN,
    Notifikasi.Jenis.PERMOHONAN_JADWAL,
}


def pengaturan_untuk(user):
    pengaturan, _ = PengaturanNotifikasi.objects.get_or_create(user=user)
    return pengaturan


def kanal_pengingat_tersedia(pengaturan, user):
    """True bila minimal satu kanal pilihan benar-benar dapat dipakai akun."""
    return bool(
        pengaturan.kanal_aplikasi
        or (pengaturan.kanal_email and bool(user.email_akademik))
    )


def waktu_kirim(target, offset_hari, jam_kirim, zona_waktu="Asia/Jakarta"):
    """Bangun waktu lokal (mis. 08.00 WIB) lalu simpan sebagai datetime aware."""
    hari = target - timedelta(days=int(offset_hari))
    lokal = datetime.combine(hari, jam_kirim)
    return timezone.make_aware(lokal, ZoneInfo(zona_waktu))


def _pengguna_penerima(milestone):
    from akademik.models import Penugasan

    penerima = {milestone.tugas_akhir.mahasiswa_id}
    dosen_ids = Penugasan.objects.filter(
        tugas_akhir_id=milestone.tugas_akhir_id,
        peran__in=[Penugasan.Peran.UTAMA, Penugasan.Peran.PENDAMPING],
    ).values_list("dosen_id", flat=True)
    penerima.update(dosen_ids)
    return list(penerima)


def _milestone_aktif(tugas_akhir_id):
    from milestone.models import Milestone

    return (
        Milestone.objects.filter(tugas_akhir_id=tugas_akhir_id, diverifikasi_pada__isnull=True)
        .order_by("urutan", "id")
        .first()
    )


def sinkronkan_pengingat_ta(tugas_akhir_id, pengguna=None):
    """Rebuild jadwal H-7/H-3/H-1 untuk milestone aktif secara idempoten.

    Baris lama dipertahankan sebagai riwayat dengan status dibatalkan. Unique
    constraint membuat dua pemanggilan bersamaan tidak membuat jadwal ganda.
    """
    from akademik.models import TugasAkhir
    from milestone.models import Milestone

    with transaction.atomic():
        milestones = list(
            Milestone.objects.select_for_update()
            .filter(tugas_akhir_id=tugas_akhir_id)
            .select_related("tugas_akhir__mahasiswa")
            .order_by("urutan", "id")
        )
        if not milestones:
            return 0

        current = next((m for m in milestones if m.diverifikasi_pada is None), None)
        pending = PengingatTerjadwal.objects.filter(
            milestone__tugas_akhir_id=tugas_akhir_id,
            status=PengingatTerjadwal.Status.TERJADWAL,
        )
        if pengguna is not None:
            pending = pending.filter(pengguna=pengguna)
        pending.update(status=PengingatTerjadwal.Status.DIBATALKAN, diubah_pada=timezone.now())

        if current is None or current.target is None:
            return 0
        if current.tugas_akhir.status != TugasAkhir.Status.AKTIF:
            return 0

        penerima_ids = [pengguna.pk] if pengguna is not None else _pengguna_penerima(current)
        dibuat = 0
        sekarang = timezone.now()
        for user_id in penerima_ids:
            from django.contrib.auth import get_user_model

            user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
            if user is None or user.role not in {Role.MAHASISWA, Role.DOSEN}:
                continue
            pengaturan = pengaturan_untuk(user)
            if not pengaturan.pengingat_aktif or not kanal_pengingat_tersedia(pengaturan, user):
                continue
            for offset, field in OFFSET_FIELD.items():
                if not getattr(pengaturan, field):
                    continue
                kirim_pada = waktu_kirim(
                    current.target,
                    offset,
                    pengaturan.jam_kirim,
                    pengaturan.zona_waktu,
                )
                # H-x yang sudah lewat tidak dikirim susulan; tenggat terlewat
                # memiliki notifikasi terpisah.
                if kirim_pada <= sekarang:
                    continue
                item, dibuat_baru = PengingatTerjadwal.objects.get_or_create(
                    pengguna=user,
                    milestone=current,
                    offset_hari=offset,
                    tanggal_target=current.target,
                    defaults={
                        "jadwal_kirim": kirim_pada,
                        "status": PengingatTerjadwal.Status.TERJADWAL,
                    },
                )
                if not dibuat_baru and item.status == PengingatTerjadwal.Status.DIBATALKAN:
                    item.jadwal_kirim = kirim_pada
                    item.status = PengingatTerjadwal.Status.TERJADWAL
                    item.notifikasi = None
                    item.dikirim_pada = None
                    item.save(
                        update_fields=[
                            "jadwal_kirim", "status", "notifikasi", "dikirim_pada", "diubah_pada"
                        ]
                    )
                dibuat += int(dibuat_baru)
        return dibuat


def sinkronkan_pengingat_pengguna(user):
    """Perbarui semua jadwal yang relevan setelah preferensi pengguna berubah."""
    from akademik.models import Penugasan, TugasAkhir
    from milestone.models import Milestone

    if user.role == Role.MAHASISWA:
        ta_ids = TugasAkhir.objects.filter(
            mahasiswa=user, status=TugasAkhir.Status.AKTIF
        ).values_list("id", flat=True)
    elif user.role == Role.DOSEN:
        ta_ids = Penugasan.objects.filter(
            dosen=user,
            peran__in=[Penugasan.Peran.UTAMA, Penugasan.Peran.PENDAMPING],
            tugas_akhir__status=TugasAkhir.Status.AKTIF,
        ).values_list("tugas_akhir_id", flat=True)
    else:
        return
    for ta_id in ta_ids:
        sinkronkan_pengingat_ta(ta_id, pengguna=user)


def jadwalkan_hitung_ulang(tugas_akhir_id):
    """Kirim task rekonsiliasi setelah commit; sinkronisasi DB sudah dilakukan sinkron."""
    def antrekan():
        try:
            from .tasks import hitung_ulang_pengingat_ta

            hitung_ulang_pengingat_ta.delay(tugas_akhir_id)
        except Exception:
            # Redis/worker dapat tidak tersedia pada development; jadwal DB tetap sinkron.
            import logging

            logging.getLogger(__name__).exception("Tidak dapat mengantrekan rekonsiliasi pengingat")

    transaction.on_commit(antrekan, robust=True)


def boleh_kirim_email(user, jenis):
    pengaturan = PengaturanNotifikasi.objects.filter(user=user).first()
    if not pengaturan or not pengaturan.kanal_email or not user.email_akademik:
        return False
    if user.role == Role.DOSEN and jenis in JENIS_DOKUMEN and not pengaturan.dokumen_feedback_aktif:
        return False
    if user.role == Role.DOSEN and jenis in JENIS_JADWAL and not pengaturan.jadwal_bimbingan_aktif:
        return False
    return True


def notify(user, jenis, judul, isi="", tautan="", *, kunci_idempoten=None):
    """Buat notifikasi pada kanal aktif dan antrekan email sesuai preferensi akun."""
    if jenis not in Notifikasi.Jenis.values:
        raise ValueError(f"Jenis notifikasi tidak dikenal: {jenis}")

    pengaturan = PengaturanNotifikasi.objects.filter(user=user).first()
    tampil = pengaturan.kanal_aplikasi if pengaturan else True
    if pengaturan and user.role == Role.DOSEN and jenis in JENIS_DOKUMEN and not pengaturan.dokumen_feedback_aktif:
        return None
    if pengaturan and user.role == Role.DOSEN and jenis in JENIS_JADWAL and not pengaturan.jadwal_bimbingan_aktif:
        return None
    email_aktif = boleh_kirim_email(user, jenis)
    if not tampil and not email_aktif:
        return None

    defaults = {
        "jenis": jenis,
        "judul": judul[:200],
        "isi": isi,
        "tautan": tautan[:255],
        "tampil_di_aplikasi": tampil,
    }
    if kunci_idempoten:
        notif, dibuat = Notifikasi.objects.get_or_create(
            user=user, kunci_idempoten=kunci_idempoten, defaults=defaults
        )
    else:
        notif = Notifikasi.objects.create(user=user, **defaults)
        dibuat = True

    if email_aktif and notif.email_dikirim_pada is None:
        def antrekan_email():
            try:
                from .tasks import kirim_email_notifikasi

                kirim_email_notifikasi.delay(notif.pk)
            except Exception:
                import logging

                logging.getLogger(__name__).exception("Tidak dapat mengantrekan email notifikasi")

        transaction.on_commit(antrekan_email, robust=True)
    return notif


def daftar_milestone_pratinjau(user, pengaturan):
    """Hitung jadwal nyata dari milestone aktif, tanpa membuat baris jadwal baru."""
    from akademik.models import Penugasan, TugasAkhir
    from milestone.models import Milestone

    if user.role == Role.MAHASISWA:
        ta_qs = TugasAkhir.objects.filter(mahasiswa=user, status=TugasAkhir.Status.AKTIF)
    elif user.role == Role.DOSEN:
        ta_qs = TugasAkhir.objects.filter(
            status=TugasAkhir.Status.AKTIF,
            penugasan__dosen=user,
            penugasan__peran__in=[Penugasan.Peran.UTAMA, Penugasan.Peran.PENDAMPING],
        )
    else:
        return []

    hasil = []
    if not pengaturan.pengingat_aktif or not kanal_pengingat_tersedia(pengaturan, user):
        return hasil
    sekarang = timezone.now()
    for ta in ta_qs.select_related("mahasiswa").distinct().order_by("mahasiswa__identifier")[:100]:
        ms = _milestone_aktif(ta.pk)
        if ms is None or ms.target is None:
            continue
        for offset, field in OFFSET_FIELD.items():
            if not pengaturan.pengingat_aktif or not getattr(pengaturan, field):
                continue
            waktu = waktu_kirim(ms.target, offset, pengaturan.jam_kirim, pengaturan.zona_waktu)
            if waktu <= sekarang:
                continue
            hasil.append(
                {
                    "milestone_id": ms.pk,
                    "milestone": ms.nama,
                    "mahasiswa": ta.mahasiswa.nama_lengkap,
                    "identifier": ta.mahasiswa.identifier,
                    "target": ms.target,
                    "offset_hari": offset,
                    "jadwal_kirim": waktu,
                    "zona_waktu": pengaturan.zona_waktu,
                }
            )
    return sorted(hasil, key=lambda item: (item["jadwal_kirim"], item["identifier"]))
