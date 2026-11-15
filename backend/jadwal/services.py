from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone

from accounts.models import Role
from akademik.models import Penugasan, TugasAkhir
from notifikasi.models import Notifikasi
from notifikasi.services import notify

from .models import Bimbingan

TAUTAN_MAHASISWA = "/mahasiswa/jadwal"
TAUTAN_DOSEN = "/dosen/dashboard"


class JadwalError(Exception):
    """Pelanggaran aturan jadwal; pesan aman ditampilkan ke pengguna."""


def validasi_rentang_waktu(mulai, selesai, sekarang=None):
    sekarang = sekarang or timezone.now()
    if mulai <= sekarang:
        raise JadwalError("Jadwal tidak boleh berada di masa lalu.")
    if selesai <= mulai:
        raise JadwalError("Jam selesai harus setelah jam mulai.")


def _validasi_lokasi(mode, lokasi_atau_tautan, wajib=False):
    nilai = (lokasi_atau_tautan or "").strip()
    if wajib and not nilai:
        if mode == Bimbingan.Mode.DARING:
            raise JadwalError("Tautan rapat wajib diisi saat menyetujui bimbingan daring.")
        raise JadwalError("Lokasi bimbingan wajib diisi saat menyetujui bimbingan luring.")
    if nilai and mode == Bimbingan.Mode.DARING:
        try:
            URLValidator(schemes=["http", "https"])(nilai)
        except ValidationError:
            raise JadwalError("Tautan bimbingan daring harus berupa URL http atau https yang valid.") from None
    return nilai


def ta_aktif_mahasiswa(user):
    return TugasAkhir.objects.filter(
        mahasiswa=user,
        status=TugasAkhir.Status.AKTIF,
    ).select_related("periode").first()


def ta_terkini_mahasiswa(user):
    semua = TugasAkhir.objects.filter(mahasiswa=user).select_related("periode")
    return semua.filter(status=TugasAkhir.Status.AKTIF).first() or semua.order_by("-id").first()


def dosen_terdaftar(ta, dosen_id):
    return Penugasan.objects.filter(
        tugas_akhir=ta,
        dosen_id=dosen_id,
        dosen__role=Role.DOSEN,
    ).select_related("dosen").first()


def payload_bimbingan(item):
    assignment = Penugasan.objects.filter(
        tugas_akhir_id=item.tugas_akhir_id,
        dosen_id=item.dosen_id,
    ).first()
    return {
        "id": item.pk,
        "tugas_akhir": {
            "id": item.tugas_akhir_id,
            "judul": item.tugas_akhir.judul,
        },
        "mahasiswa": {
            "id": item.tugas_akhir.mahasiswa_id,
            "identifier": item.tugas_akhir.mahasiswa.identifier,
            "nama_lengkap": item.tugas_akhir.mahasiswa.nama_lengkap,
        },
        "dosen": {
            "id": item.dosen_id,
            "identifier": item.dosen.identifier,
            "nama_lengkap": item.dosen.nama_lengkap,
            "peran": assignment.peran if assignment else "",
            "peran_label": assignment.get_peran_display() if assignment else "Dosen",
        },
        "mulai": item.mulai.isoformat(),
        "selesai": item.selesai.isoformat(),
        "mode": item.mode,
        "mode_label": item.get_mode_display(),
        "lokasi_atau_tautan": item.lokasi_atau_tautan,
        "agenda": item.agenda,
        "status": item.status,
        "status_label": item.get_status_display(),
        "menggantikan": item.menggantikan_id,
        "alasan_penolakan": item.alasan_penolakan,
        "dibuat_pada": item.dibuat_pada.isoformat(),
    }


def data_jadwal_mahasiswa(user):
    # Riwayat tetap dapat dibaca meski TA terakhir sudah selesai/dibatalkan.
    ta = ta_terkini_mahasiswa(user)
    if ta is None:
        return {
            "tugas_akhir": None,
            "dosen_tujuan": [],
            "mendatang": [],
            "riwayat": [],
        }

    assignments = list(
        Penugasan.objects.filter(tugas_akhir=ta, dosen__role=Role.DOSEN)
        .select_related("dosen")
        .order_by("peran", "dosen__nama_lengkap")
    ) if ta.status == TugasAkhir.Status.AKTIF else []
    now = timezone.now()
    status_aktif = [Bimbingan.Status.MENUNGGU_KONFIRMASI, Bimbingan.Status.DISETUJUI]
    base = Bimbingan.objects.filter(tugas_akhir=ta).select_related(
        "tugas_akhir__mahasiswa", "dosen", "menggantikan"
    )
    mendatang = base.filter(status__in=status_aktif, selesai__gte=now).order_by("mulai", "id")
    riwayat = base.filter(
        Q(status__in=[Bimbingan.Status.DITOLAK, Bimbingan.Status.DIBATALKAN, Bimbingan.Status.SELESAI])
        | Q(selesai__lt=now)
    ).order_by("-mulai", "-id")

    return {
        "tugas_akhir": {"id": ta.pk, "judul": ta.judul, "periode": ta.periode.label},
        "dosen_tujuan": [
            {
                "id": item.dosen_id,
                "identifier": item.dosen.identifier,
                "nama_lengkap": item.dosen.nama_lengkap,
                "peran": item.peran,
                "peran_label": item.get_peran_display(),
            }
            for item in assignments
        ],
        "mendatang": [payload_bimbingan(item) for item in mendatang],
        "riwayat": [payload_bimbingan(item) for item in riwayat],
    }


def permohonan_masuk_dosen(user):
    qs = Bimbingan.objects.filter(
        dosen=user,
        tugas_akhir__penugasan__dosen=user,
        tugas_akhir__status=TugasAkhir.Status.AKTIF,
        status=Bimbingan.Status.MENUNGGU_KONFIRMASI,
    ).distinct().select_related("tugas_akhir__mahasiswa", "tugas_akhir", "dosen", "menggantikan")
    qs = qs.order_by("dibuat_pada", "id")
    hasil = [payload_bimbingan(item) for item in qs]
    return {"jumlah": len(hasil), "hasil": hasil}


def _ambil_milik_mahasiswa(user, pk, lock=False):
    qs = Bimbingan.objects.select_related("tugas_akhir__mahasiswa", "tugas_akhir", "dosen", "menggantikan")
    if lock:
        qs = qs.select_for_update()
    item = qs.filter(tugas_akhir__mahasiswa=user).filter(tugas_akhir__status=TugasAkhir.Status.AKTIF).filter(pk=pk).first()
    if item is None:
        raise Http404
    return item


def _ambil_milik_dosen(user, pk, lock=False):
    qs = Bimbingan.objects.select_related("tugas_akhir__mahasiswa", "tugas_akhir", "dosen", "menggantikan")
    if lock:
        qs = qs.select_for_update()
    item = qs.filter(dosen=user, tugas_akhir__penugasan__dosen=user, pk=pk).distinct().first()
    if item is None:
        raise Http404
    return item


def buat_permohonan(*, mahasiswa, dosen_id, mulai, selesai, mode, lokasi_atau_tautan="", agenda=""):
    ta = ta_aktif_mahasiswa(mahasiswa)
    if ta is None:
        raise JadwalError("Tugas akhir aktif belum terdaftar.")
    assignment = dosen_terdaftar(ta, dosen_id)
    if assignment is None:
        raise Http404
    validasi_rentang_waktu(mulai, selesai)
    lokasi = _validasi_lokasi(mode, lokasi_atau_tautan, wajib=False)
    with transaction.atomic():
        item = Bimbingan.objects.create(
            tugas_akhir=ta,
            dosen=assignment.dosen,
            mulai=mulai,
            selesai=selesai,
            mode=mode,
            lokasi_atau_tautan=lokasi,
            agenda=(agenda or "").strip(),
        )
        notify(
            assignment.dosen,
            Notifikasi.Jenis.PERMOHONAN_JADWAL,
            "Permohonan jadwal bimbingan",
            f"{mahasiswa.nama_lengkap} mengajukan jadwal bimbingan.",
            f"{TAUTAN_DOSEN}?jadwal={item.pk}",
        )
    return item


def reschedule_mahasiswa(*, mahasiswa, bimbingan_id, mulai, selesai, mode, lokasi_atau_tautan="", agenda=""):
    validasi_rentang_waktu(mulai, selesai)
    lokasi = _validasi_lokasi(mode, lokasi_atau_tautan, wajib=False)
    with transaction.atomic():
        lama = _ambil_milik_mahasiswa(mahasiswa, bimbingan_id, lock=True)
        if dosen_terdaftar(lama.tugas_akhir, lama.dosen_id) is None:
            raise Http404
        if lama.status not in {Bimbingan.Status.MENUNGGU_KONFIRMASI, Bimbingan.Status.DISETUJUI}:
            raise JadwalError("Hanya jadwal mendatang yang menunggu konfirmasi atau disetujui yang dapat di-reschedule.")
        if lama.selesai < timezone.now():
            raise JadwalError("Jadwal yang sudah berlalu tidak dapat di-reschedule.")
        if lama.permohonan_pengganti.filter(status=Bimbingan.Status.MENUNGGU_KONFIRMASI).exists():
            raise JadwalError("Sudah ada permohonan reschedule yang menunggu konfirmasi untuk jadwal ini.")
        baru = Bimbingan.objects.create(
            tugas_akhir=lama.tugas_akhir,
            dosen=lama.dosen,
            mulai=mulai,
            selesai=selesai,
            mode=mode,
            lokasi_atau_tautan=lokasi,
            agenda=(agenda or "").strip(),
            menggantikan=lama,
        )
        # Permohonan yang belum pernah disetujui digantikan langsung. Jadwal yang
        # sudah disetujui tetap berlaku sampai penggantinya disetujui dosen.
        if lama.status == Bimbingan.Status.MENUNGGU_KONFIRMASI:
            lama.status = Bimbingan.Status.DIBATALKAN
            lama.save(update_fields=["status", "diubah_pada"])
            notify(
                lama.dosen,
                Notifikasi.Jenis.JADWAL_DIBATALKAN,
                "Permohonan jadwal digantikan",
                f"{mahasiswa.nama_lengkap} mengajukan waktu pengganti untuk permohonan sebelumnya.",
                TAUTAN_DOSEN,
            )
        notify(
            baru.dosen,
            Notifikasi.Jenis.PERMOHONAN_JADWAL,
            "Permohonan reschedule bimbingan",
            f"{mahasiswa.nama_lengkap} mengusulkan waktu pengganti untuk jadwal bimbingan.",
            f"{TAUTAN_DOSEN}?jadwal={baru.pk}",
        )
    return baru


def _periksa_bentrok(*, dosen, mulai, selesai, kecuali_ids=()):
    # Kunci baris dosen agar dua permintaan persetujuan bersamaan tidak lolos
    # pemeriksaan overlap untuk dosen yang sama.
    get_user_model().objects.select_for_update().get(pk=dosen.pk)
    qs = Bimbingan.objects.filter(
        dosen=dosen,
        status=Bimbingan.Status.DISETUJUI,
        mulai__lt=selesai,
        selesai__gt=mulai,
    )
    if kecuali_ids:
        qs = qs.exclude(pk__in=list(kecuali_ids))
    if qs.exists():
        raise JadwalError("Jadwal bentrok: dosen sudah memiliki bimbingan lain yang disetujui pada rentang waktu tersebut.")


def setujui_permohonan(*, dosen, bimbingan_id, lokasi_atau_tautan):
    with transaction.atomic():
        item = _ambil_milik_dosen(dosen, bimbingan_id, lock=True)
        if item.status != Bimbingan.Status.MENUNGGU_KONFIRMASI:
            raise JadwalError("Permohonan ini sudah diproses dan tidak dapat disetujui lagi.")
        validasi_rentang_waktu(item.mulai, item.selesai)
        lokasi = _validasi_lokasi(item.mode, lokasi_atau_tautan, wajib=True)
        old = item.menggantikan
        kecuali = [old.pk] if old and old.status == Bimbingan.Status.DISETUJUI else []
        _periksa_bentrok(dosen=dosen, mulai=item.mulai, selesai=item.selesai, kecuali_ids=kecuali)
        if old and old.status == Bimbingan.Status.DISETUJUI:
            old.status = Bimbingan.Status.DIBATALKAN
            old.save(update_fields=["status", "diubah_pada"])
            notify(
                old.tugas_akhir.mahasiswa,
                Notifikasi.Jenis.JADWAL_DIBATALKAN,
                "Jadwal bimbingan lama dibatalkan",
                "Jadwal lama digantikan oleh waktu bimbingan yang baru disetujui.",
                TAUTAN_MAHASISWA,
            )
        item.status = Bimbingan.Status.DISETUJUI
        item.lokasi_atau_tautan = lokasi
        item.alasan_penolakan = ""
        item.save(update_fields=["status", "lokasi_atau_tautan", "alasan_penolakan", "diubah_pada"])
        notify(
            item.tugas_akhir.mahasiswa,
            Notifikasi.Jenis.JADWAL_DISETUJUI,
            "Jadwal bimbingan disetujui",
            f"Jadwal bimbingan pada {timezone.localtime(item.mulai):%d %b %Y %H:%M} telah disetujui.",
            TAUTAN_MAHASISWA,
        )
    return item


def tolak_permohonan(*, dosen, bimbingan_id, alasan):
    alasan = (alasan or "").strip()
    if not alasan:
        raise JadwalError("Alasan penolakan wajib diisi.")
    with transaction.atomic():
        item = _ambil_milik_dosen(dosen, bimbingan_id, lock=True)
        if item.status != Bimbingan.Status.MENUNGGU_KONFIRMASI:
            raise JadwalError("Permohonan ini sudah diproses dan tidak dapat ditolak lagi.")
        item.status = Bimbingan.Status.DITOLAK
        item.alasan_penolakan = alasan
        item.save(update_fields=["status", "alasan_penolakan", "diubah_pada"])
        notify(
            item.tugas_akhir.mahasiswa,
            Notifikasi.Jenis.JADWAL_DITOLAK,
            "Permohonan jadwal ditolak",
            alasan,
            TAUTAN_MAHASISWA,
        )
    return item


def usulkan_waktu_lain(*, dosen, bimbingan_id, mulai, selesai, lokasi_atau_tautan=None):
    validasi_rentang_waktu(mulai, selesai)
    with transaction.atomic():
        item = _ambil_milik_dosen(dosen, bimbingan_id, lock=True)
        if item.status != Bimbingan.Status.MENUNGGU_KONFIRMASI:
            raise JadwalError("Waktu hanya dapat diusulkan untuk permohonan yang menunggu konfirmasi.")
        if lokasi_atau_tautan is not None:
            lokasi = _validasi_lokasi(item.mode, lokasi_atau_tautan, wajib=False)
            item.lokasi_atau_tautan = lokasi
        item.mulai = mulai
        item.selesai = selesai
        item.save(update_fields=["mulai", "selesai", "lokasi_atau_tautan", "diubah_pada"])
        notify(
            item.tugas_akhir.mahasiswa,
            Notifikasi.Jenis.JADWAL_DIUSULKAN,
            "Dosen mengusulkan waktu bimbingan lain",
            f"Dosen mengusulkan waktu {timezone.localtime(mulai):%d %b %Y %H:%M}. Periksa jadwal terbaru pada menu Jadwal bimbingan.",
            TAUTAN_MAHASISWA,
        )
    return item


def bimbingan_terdekat_mahasiswa(ta):
    if ta is None or ta.status != TugasAkhir.Status.AKTIF:
        return None
    now = timezone.now()
    item = (
        Bimbingan.objects.filter(
            tugas_akhir=ta,
            status__in=[Bimbingan.Status.MENUNGGU_KONFIRMASI, Bimbingan.Status.DISETUJUI],
            selesai__gte=now,
        )
        .select_related("tugas_akhir__mahasiswa", "dosen", "menggantikan")
        .order_by("mulai", "id")
        .first()
    )
    return payload_bimbingan(item) if item else None


def permohonan_jadwal_dashboard_dosen(user, batas=6):
    qs = Bimbingan.objects.filter(
        dosen=user,
        tugas_akhir__penugasan__dosen=user,
        tugas_akhir__status=TugasAkhir.Status.AKTIF,
        status=Bimbingan.Status.MENUNGGU_KONFIRMASI,
    ).distinct().select_related("tugas_akhir__mahasiswa", "tugas_akhir", "dosen", "menggantikan")
    total = qs.count()
    hasil = [payload_bimbingan(item) for item in qs.order_by("dibuat_pada", "id")[:batas]]
    return {"jumlah": total, "hasil": hasil}
