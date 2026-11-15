from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from akademik.models import TugasAkhir
from milestone.models import Milestone

from .models import Notifikasi, PengaturanNotifikasi, PengingatTerjadwal
from .services import (
    JENIS_DOKUMEN,
    JENIS_JADWAL,
    boleh_kirim_email,
    kanal_pengingat_tersedia,
    notify,
    sinkronkan_pengingat_ta,
)


@shared_task(name="notifikasi.hitung_ulang_pengingat_ta")
def hitung_ulang_pengingat_ta(tugas_akhir_id):
    """Rekonsiliasi jadwal setelah perubahan target/verifikasi milestone."""
    sinkronkan_pengingat_ta(tugas_akhir_id)
    return {"tugas_akhir_id": tugas_akhir_id, "status": "ok"}


@shared_task(
    name="notifikasi.hitung_ulang_semua_pengingat",
    ignore_result=False,
)
def hitung_ulang_semua_pengingat():
    """Perbaikan berkala bila worker pernah mati ketika sebuah perubahan terjadi."""
    ids = TugasAkhir.objects.filter(status=TugasAkhir.Status.AKTIF).values_list("id", flat=True)
    jumlah = 0
    for ta_id in ids.iterator(chunk_size=200):
        jumlah += sinkronkan_pengingat_ta(ta_id)
    return {"jadwal_dibuat_ulang": jumlah}


@shared_task(name="notifikasi.kirim_pengingat_jatuh_tempo")
def kirim_pengingat_jatuh_tempo():
    """Kirim pengingat yang jatuh tempo; row lock + unique key mencegah duplikasi."""
    sekarang = timezone.now()
    ids = list(
        PengingatTerjadwal.objects.filter(
            status=PengingatTerjadwal.Status.TERJADWAL,
            jadwal_kirim__lte=sekarang,
        )
        .order_by("jadwal_kirim", "id")
        .values_list("id", "milestone_id")[:500]
    )
    terkirim = 0
    dibatalkan = 0
    for reminder_id, milestone_id in ids:
        with transaction.atomic():
            # Urutan lock sama dengan perubahan target: milestone dahulu, baru jadwal.
            # Ini menghindari deadlock dan mencegah pengiriman memakai target usang.
            ms = (
                Milestone.objects.select_for_update()
                .select_related("tugas_akhir")
                .filter(pk=milestone_id)
                .first()
            )
            item = (
                PengingatTerjadwal.objects.select_for_update()
                .select_related("pengguna")
                .filter(pk=reminder_id, milestone_id=milestone_id)
                .first()
            )
            if (
                ms is None
                or item is None
                or item.status != PengingatTerjadwal.Status.TERJADWAL
            ):
                continue
            aktif = (
                Milestone.objects.filter(
                    tugas_akhir_id=ms.tugas_akhir_id,
                    diverifikasi_pada__isnull=True,
                )
                .order_by("urutan", "id")
                .values_list("id", flat=True)
                .first()
            )
            pref = PengaturanNotifikasi.objects.filter(user=item.pengguna).first()
            field = {7: "h_minus_7", 3: "h_minus_3", 1: "h_minus_1"}.get(item.offset_hari)
            from akademik.models import Penugasan

            relasi_penerima_valid = (
                item.pengguna.role == "mahasiswa"
                and ms.tugas_akhir.mahasiswa_id == item.pengguna_id
            ) or (
                item.pengguna.role == "dosen"
                and Penugasan.objects.filter(
                    tugas_akhir_id=ms.tugas_akhir_id,
                    dosen_id=item.pengguna_id,
                    peran__in=[Penugasan.Peran.UTAMA, Penugasan.Peran.PENDAMPING],
                ).exists()
            )
            masih_berlaku = (
                relasi_penerima_valid
                and ms.diverifikasi_pada is None
                and ms.target == item.tanggal_target
                and ms.tugas_akhir.status == TugasAkhir.Status.AKTIF
                and aktif == ms.pk
                and pref is not None
                and pref.pengingat_aktif
                and kanal_pengingat_tersedia(pref, item.pengguna)
                and field is not None
                and getattr(pref, field)
            )
            if not masih_berlaku:
                item.status = PengingatTerjadwal.Status.DIBATALKAN
                item.save(update_fields=["status", "diubah_pada"])
                dibatalkan += 1
                continue

            notif = notify(
                item.pengguna,
                Notifikasi.Jenis.PENGINGAT,
                f"Pengingat tenggat H-{item.offset_hari}: {ms.nama}",
                f"Target milestone {ms.nama} jatuh pada {item.tanggal_target:%d-%m-%Y}. Ini adalah pengingat H-{item.offset_hari}.",
                "/mahasiswa/milestone" if item.pengguna.role == "mahasiswa" else "/dosen/mahasiswa",
                kunci_idempoten=f"pengingat-terjadwal:{item.pk}",
            )
            item.status = PengingatTerjadwal.Status.TERKIRIM
            item.notifikasi = notif
            item.dikirim_pada = sekarang
            item.save(update_fields=["status", "notifikasi", "dikirim_pada", "diubah_pada"])
            terkirim += 1

    return {"diperiksa": len(ids), "terkirim": terkirim, "dibatalkan": dibatalkan}


@shared_task(name="notifikasi.kirim_peringatan_tenggat")
def kirim_peringatan_tenggat():
    """Notifikasi terlambat terpisah, dibuat paling banyak sekali per target."""
    hari_ini = timezone.localdate()
    aktif = Milestone.objects.filter(
        tugas_akhir__status=TugasAkhir.Status.AKTIF,
        target__lt=hari_ini,
        diverifikasi_pada__isnull=True,
    ).select_related("tugas_akhir__mahasiswa")
    jumlah = 0
    for ms in aktif.iterator(chunk_size=200):
        first = (
            Milestone.objects.filter(
                tugas_akhir_id=ms.tugas_akhir_id,
                diverifikasi_pada__isnull=True,
            )
            .order_by("urutan", "id")
            .values_list("id", flat=True)
            .first()
        )
        if first != ms.pk:
            continue
        from .services import _pengguna_penerima

        from django.contrib.auth import get_user_model
        from .services import pengaturan_untuk

        for user_id in _pengguna_penerima(ms):
            user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
            if user is None:
                continue
            pref = pengaturan_untuk(user)
            if not pref.pengingat_aktif or not kanal_pengingat_tersedia(pref, user):
                continue
            kunci = f"tenggat-terlewat:{user_id}:{ms.pk}:{ms.target.isoformat()}"
            sudah_ada = Notifikasi.objects.filter(user=user, kunci_idempoten=kunci).exists()
            hasil_notifikasi = notify(
                user,
                Notifikasi.Jenis.TENGGAT_TERLEWAT,
                f"Tenggat terlewat: {ms.nama}",
                f"Target milestone {ms.nama} adalah {ms.target:%d-%m-%Y} dan belum diverifikasi.",
                "/mahasiswa/milestone" if user.role == "mahasiswa" else "/dosen/mahasiswa?tab=terlambat",
                kunci_idempoten=kunci,
            )
            if hasil_notifikasi is not None and not sudah_ada:
                jumlah += 1
    return {"peringatan_dibuat": jumlah}


@shared_task(name="notifikasi.kirim_email_notifikasi", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def kirim_email_notifikasi(notifikasi_id):
    """Kirim email event notifikasi sekali per row selama transaksi DB terkunci."""
    with transaction.atomic():
        item = (
            Notifikasi.objects.select_for_update()
            .select_related("user")
            .filter(pk=notifikasi_id)
            .first()
        )
        if item is None or item.email_dikirim_pada is not None:
            return {"dikirim": False, "alasan": "sudah diproses atau tidak ditemukan"}
        if not boleh_kirim_email(item.user, item.jenis):
            return {"dikirim": False, "alasan": "kanal email tidak aktif"}
        isi = item.isi or item.judul
        tautan = item.tautan or ""
        body = f"{item.judul}\n\n{isi}"
        if tautan:
            if tautan.startswith("/"):
                tautan = f"{settings.FRONTEND_BASE_URL.rstrip('/')}{tautan}"
            body += f"\n\nBuka SIMONTA: {tautan}"
        hasil = send_mail(
            subject=f"SIMONTA — {item.judul}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[item.user.email_akademik],
            fail_silently=False,
        )
        if hasil:
            item.email_dikirim_pada = timezone.now()
            item.save(update_fields=["email_dikirim_pada"])
        return {"dikirim": bool(hasil), "notifikasi_id": item.pk}


@shared_task(
    name="notifikasi.kirim_ringkasan_mingguan",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def kirim_ringkasan_mingguan():
    """Ringkasan mingguan dikirim Senin pagi sesuai zona waktu aplikasi (WIB)."""
    hari_ini = timezone.localdate()
    awal = hari_ini - timedelta(days=7)
    jumlah = 0
    prefs = PengaturanNotifikasi.objects.filter(
        ringkasan_mingguan=True,
        user__is_active=True,
        user__email_akademik__isnull=False,
    ).exclude(user__email_akademik="").select_related("user")
    for pref in prefs.iterator(chunk_size=200):
        user = pref.user
        kunci = f"ringkasan-mingguan:{user.pk}:{hari_ini.isoformat()}"
        with transaction.atomic():
            item, _ = Notifikasi.objects.get_or_create(
                user=user,
                kunci_idempoten=kunci,
                defaults={
                    "jenis": Notifikasi.Jenis.RINGKASAN_MINGGUAN,
                    "judul": "Ringkasan mingguan SIMONTA",
                    "isi": "Ringkasan notifikasi dan aktivitas SIMONTA selama tujuh hari terakhir.",
                    "tautan": f"/{user.role}/notifikasi",
                    "tampil_di_aplikasi": pref.kanal_aplikasi,
                },
            )
            # Kunci row membuat retry/dua worker tidak mengirim email mingguan ganda.
            item = Notifikasi.objects.select_for_update().get(pk=item.pk)
            if item.email_dikirim_pada:
                continue
            notifikasi = list(
                Notifikasi.objects.filter(
                    user=user,
                    dibuat_pada__date__gte=awal,
                    dibuat_pada__date__lt=hari_ini,
                )
                .exclude(jenis=Notifikasi.Jenis.RINGKASAN_MINGGUAN)
                .order_by("-dibuat_pada")[:10]
            )
            if not notifikasi:
                ringkasan = "Tidak ada notifikasi baru selama tujuh hari terakhir."
            else:
                ringkasan = "Aktivitas dan notifikasi terbaru:\n" + "\n".join(
                    f"- {n.judul}: {n.isi[:180]}" for n in notifikasi
                )
            isi_email = (
                f"Halo {user.nama_lengkap},\n\n{ringkasan}\n\n"
                f"Buka SIMONTA: {settings.FRONTEND_BASE_URL.rstrip('/')}/{user.role}/notifikasi"
            )
            hasil = send_mail(
                subject="Ringkasan mingguan SIMONTA",
                message=isi_email,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email_akademik],
                fail_silently=False,
            )
            if hasil:
                item.email_dikirim_pada = timezone.now()
                item.save(update_fields=["email_dikirim_pada"])
                jumlah += 1
    return {"ringkasan_dikirim": jumlah}
