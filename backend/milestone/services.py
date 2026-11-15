from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.formats import date_format

from akademik.models import MilestoneTemplate, TugasAkhir
from audit.models import AuditLog
from audit.services import catat_audit, diff, snapshot
from notifikasi.models import Notifikasi
from notifikasi.services import jadwalkan_hitung_ulang, notify, sinkronkan_pengingat_ta

from .models import Milestone

TAUTAN_MAHASISWA = "/mahasiswa/milestone"


class MilestoneError(Exception):
    """Pelanggaran aturan milestone; pesannya aman ditampilkan ke pengguna."""


class Status:
    DISETUJUI = "disetujui"
    AKTIF = "aktif"
    TERLAMBAT = "terlambat"
    TERKUNCI = "terkunci"
    BELUM_TERJADWAL = "belum_terjadwal"
    CHOICES = [
        (DISETUJUI, "Disetujui"),
        (AKTIF, "Aktif"),
        (TERLAMBAT, "Terlambat"),
        (TERKUNCI, "Terkunci"),
        (BELUM_TERJADWAL, "Belum terjadwal"),
    ]


@dataclass
class ItemMilestone:
    id: int
    urutan: int
    nama: str
    bobot: Decimal
    target: date | None
    status: str
    tahap_aktif: bool
    terkunci: bool
    tingkat_penyelesaian: int
    diverifikasi_pada: datetime | None


@dataclass
class Timeline:
    items: list[ItemMilestone]
    progres: Decimal
    jumlah_diverifikasi: int
    tahap_aktif_id: int | None


# --- Perhitungan murni (BR-01, BR-02) ---


def hitung_progres(milestones) -> Decimal:
    """P = jumlah (bobot x tingkat_penyelesaian / 100), hanya milestone terverifikasi."""
    total = sum(
        (m.bobot * m.tingkat_penyelesaian / Decimal(100) for m in milestones if m.diverifikasi_pada),
        Decimal("0"),
    )
    return total.quantize(Decimal("0.01"))


def cari_tahap_aktif(milestones):
    """Tahap aktif = milestone pertama (menurut urutan) yang belum diverifikasi."""
    return next((m for m in sorted(milestones, key=lambda m: m.urutan) if not m.diverifikasi_pada), None)


def hitung_status(m, aktif_id, hari_ini: date) -> str:
    if m.diverifikasi_pada:
        return Status.DISETUJUI
    if m.target is None:
        return Status.BELUM_TERJADWAL
    if m.id != aktif_id:
        return Status.TERKUNCI
    return Status.TERLAMBAT if m.target < hari_ini else Status.AKTIF


def bangun_timeline(milestones, hari_ini: date | None = None) -> Timeline:
    hari_ini = hari_ini or timezone.localdate()
    daftar = sorted(milestones, key=lambda m: m.urutan)
    aktif = cari_tahap_aktif(daftar)
    aktif_id = aktif.id if aktif else None
    items = [
        ItemMilestone(
            id=m.id,
            urutan=m.urutan,
            nama=m.nama,
            bobot=m.bobot,
            target=m.target,
            status=hitung_status(m, aktif_id, hari_ini),
            tahap_aktif=m.id == aktif_id,
            terkunci=m.diverifikasi_pada is None and m.id != aktif_id,
            tingkat_penyelesaian=m.tingkat_penyelesaian,
            diverifikasi_pada=m.diverifikasi_pada,
        )
        for m in daftar
    ]
    return Timeline(
        items=items,
        progres=hitung_progres(daftar),
        jumlah_diverifikasi=sum(1 for m in daftar if m.diverifikasi_pada),
        tahap_aktif_id=aktif_id,
    )


def timeline_ta(tugas_akhir: TugasAkhir, hari_ini: date | None = None) -> Timeline:
    return bangun_timeline(list(tugas_akhir.milestone.all()), hari_ini)


# --- Aksi ---


def buat_milestone_untuk_ta(tugas_akhir: TugasAkhir):
    """Membuat milestone dari template aktif (bobot disalin sebagai snapshot).

    Dipanggil eksplisit saat TA didaftarkan; bukan signal.
    """
    with transaction.atomic():
        if tugas_akhir.milestone.exists():
            raise ValidationError("Tugas akhir ini sudah memiliki milestone.")
        MilestoneTemplate.pastikan_total_valid()
        templates = MilestoneTemplate.objects.filter(aktif=True).order_by("urutan")
        return Milestone.objects.bulk_create(
            [
                Milestone(
                    tugas_akhir=tugas_akhir,
                    template=t,
                    urutan=t.urutan,
                    nama=t.nama,
                    bobot=t.bobot,
                )
                for t in templates
            ]
        )


def _persen(nilai: Decimal) -> str:
    return format(nilai.normalize(), "f").replace(".", ",")


def tetapkan_target(milestone: Milestone, target: date | None, aktor):
    """Menetapkan/mengubah/menghapus target. Pemeriksaan pembimbing utama ada di view."""
    with transaction.atomic():
        ms = (
            Milestone.objects.select_for_update()
            .select_related("tugas_akhir__mahasiswa")
            .get(pk=milestone.pk)
        )
        if ms.diverifikasi_pada:
            raise MilestoneError("Milestone sudah diverifikasi; target tidak dapat diubah.")
        if ms.target == target:
            return ms

        sebelum = snapshot(ms)
        ms.target = target
        ms.save(update_fields=["target"])
        # BR-06: perbarui jadwal tersimpan di transaksi yang sama; Celery melakukan
        # rekonsiliasi ulang setelah commit sebagai lapisan pemulihan.
        sinkronkan_pengingat_ta(ms.tugas_akhir_id)
        jadwalkan_hitung_ulang(ms.tugas_akhir_id)
        awal, akhir = diff(sebelum, snapshot(ms))
        catat_audit(
            aktor, AuditLog.Aksi.UBAH, ms, sebelum=awal, sesudah=akhir,
            keterangan="Target milestone diubah oleh pembimbing utama",
        )
        # Titik panggil BR-06: hitung ulang pengingat H-7/H-3/H-1 (dibangun di tahap 2).
        if target is None:
            isi = f"Pembimbing utama menghapus target {ms.nama}."
        else:
            isi = f"Target {ms.nama} ditetapkan pada {date_format(target, 'j M Y')}."
        notify(
            ms.tugas_akhir.mahasiswa, Notifikasi.Jenis.MILESTONE_TARGET,
            "Target milestone diperbarui", isi, TAUTAN_MAHASISWA,
        )
        return ms


def verifikasi(milestone: Milestone, tingkat: int, aktor):
    """Memverifikasi tahap aktif (BR-03). Pemeriksaan pembimbing utama ada di view."""
    if not 0 <= tingkat <= 100:
        raise MilestoneError("Tingkat penyelesaian harus antara 0 dan 100.")
    with transaction.atomic():
        daftar = list(
            Milestone.objects.select_for_update()
            .filter(tugas_akhir_id=milestone.tugas_akhir_id)
            .order_by("urutan")
        )
        ms = next((m for m in daftar if m.pk == milestone.pk), None)
        if ms is None:
            raise MilestoneError("Milestone tidak ditemukan.")
        if ms.diverifikasi_pada:
            raise MilestoneError("Milestone ini sudah diverifikasi.")
        aktif = cari_tahap_aktif(daftar)
        if aktif is None or aktif.pk != ms.pk:
            raise MilestoneError("Verifikasi tahap sebelumnya lebih dulu; tahap ini masih terkunci.")

        sebelum = snapshot(ms)
        ms.tingkat_penyelesaian = tingkat
        ms.diverifikasi_oleh = aktor
        ms.diverifikasi_pada = timezone.now()
        ms.save(update_fields=["tingkat_penyelesaian", "diverifikasi_oleh", "diverifikasi_pada"])
        # Milestone yang diverifikasi dibatalkan; bila tahap berikutnya sudah
        # memiliki target, jadwal H-7/H-3/H-1 untuk tahap tersebut dibuat.
        sinkronkan_pengingat_ta(ms.tugas_akhir_id)
        jadwalkan_hitung_ulang(ms.tugas_akhir_id)
        awal, akhir = diff(sebelum, snapshot(ms))
        catat_audit(
            aktor, AuditLog.Aksi.UBAH, ms, sebelum=awal, sesudah=akhir,
            keterangan="Milestone diverifikasi oleh pembimbing utama",
        )
        notify(
            milestone.tugas_akhir.mahasiswa, Notifikasi.Jenis.MILESTONE_DIVERIFIKASI,
            "Milestone diverifikasi",
            f"{ms.nama} telah diverifikasi pembimbing utama. Progres Anda kini {_persen(hitung_progres(daftar))}%.",
            TAUTAN_MAHASISWA,
        )
        return ms