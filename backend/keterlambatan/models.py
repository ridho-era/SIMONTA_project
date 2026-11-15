import os
import uuid

from django.conf import settings
from django.db import models

from akademik.models import KonfigurasiDenda, JenisSanksi, TugasAkhir
from milestone.models import Milestone
from review.models import Review


def bukti_keberatan_upload_path(instance, filename):
    ekstensi = os.path.splitext(filename)[1].lower()
    return f"keberatan/{uuid.uuid4().hex}{ekstensi}"


class CatatanKeterlambatan(models.Model):
    class StatusPenilaian(models.TextChoices):
        USULAN = "usulan", "Usulan"
        KEBERATAN_DITINJAU = "keberatan_ditinjau", "Keberatan ditinjau"
        DITETAPKAN = "ditetapkan", "Ditetapkan"
        DIBATALKAN = "dibatalkan", "Dibatalkan"

    tugas_akhir = models.ForeignKey(
        TugasAkhir,
        on_delete=models.PROTECT,
        related_name="catatan_keterlambatan",
    )
    konfigurasi = models.ForeignKey(
        KonfigurasiDenda,
        on_delete=models.PROTECT,
        related_name="catatan_keterlambatan",
    )
    jenis = models.CharField(max_length=12, choices=KonfigurasiDenda.Jenis.choices)
    review = models.OneToOneField(
        Review,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="catatan_keterlambatan",
    )
    milestone = models.ForeignKey(
        Milestone,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="catatan_keterlambatan",
    )
    nama_dokumen = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nama berkas administrasi untuk catatan manual.",
    )
    tenggat = models.DateField()
    realisasi = models.DateField(null=True, blank=True)

    # Snapshot konfigurasi untuk mempertahankan dasar perhitungan catatan historis.
    tarif = models.PositiveIntegerField()
    toleransi_hari = models.PositiveSmallIntegerField(default=0)
    batas_per_catatan = models.PositiveIntegerField()
    hari_terlambat = models.PositiveIntegerField(default=0)
    hari_dikenai = models.PositiveIntegerField(default=0)
    nominal = models.PositiveIntegerField(default=0)
    label_simulasi = models.BooleanField(default=True)

    status_penilaian = models.CharField(
        max_length=24,
        choices=StatusPenilaian.choices,
        default=StatusPenilaian.USULAN,
        db_index=True,
    )
    catatan_peninjau = models.TextField(blank=True)
    ditinjau_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="catatan_keterlambatan_ditinjau",
    )
    ditinjau_pada = models.DateTimeField(null=True, blank=True)
    dibuat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="catatan_keterlambatan_dibuat",
    )
    # Kunci sumber membuat pemrosesan harian idempoten. NULL dipakai untuk catatan
    # yang belum memiliki sumber otomatis atau ketika sistem lama diimpor.
    sumber_kunci = models.CharField(max_length=180, unique=True, null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "catatan keterlambatan"
        verbose_name_plural = "catatan keterlambatan"
        ordering = ["-tenggat", "-id"]
        indexes = [
            models.Index(fields=["tugas_akhir", "status_penilaian"], name="late_ta_status_idx"),
            models.Index(fields=["jenis", "tenggat"], name="late_jenis_tenggat_idx"),
        ]

    def __str__(self):
        return f"{self.tugas_akhir.mahasiswa.identifier} · {self.get_jenis_display()} · {self.tenggat}"


class Keberatan(models.Model):
    class Status(models.TextChoices):
        DRAF = "draf", "Draf"
        DIAJUKAN = "diajukan", "Diajukan"
        PERLU_KELENGKAPAN = "perlu_kelengkapan", "Perlu kelengkapan"
        DITERIMA = "diterima", "Diterima"

    catatan = models.OneToOneField(
        CatatanKeterlambatan,
        on_delete=models.PROTECT,
        related_name="keberatan",
    )
    alasan = models.TextField()
    bukti = models.FileField(
        upload_to=bukti_keberatan_upload_path,
        max_length=255,
        null=True,
        blank=True,
    )
    nama_bukti = models.CharField(max_length=255, blank=True)
    ukuran_bukti = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.DRAF,
        db_index=True,
    )
    catatan_peninjau = models.TextField(blank=True)
    ditinjau_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="keberatan_keterlambatan_ditinjau",
    )
    ditinjau_pada = models.DateTimeField(null=True, blank=True)
    diajukan_pada = models.DateTimeField(null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "keberatan keterlambatan"
        verbose_name_plural = "keberatan keterlambatan"
        ordering = ["-diubah_pada", "-id"]

    def __str__(self):
        return f"Keberatan catatan #{self.catatan_id} ({self.get_status_display()})"


class SanksiTercatat(models.Model):
    catatan = models.OneToOneField(
        CatatanKeterlambatan,
        on_delete=models.PROTECT,
        related_name="sanksi_tercatat",
    )
    jenis_sanksi = models.ForeignKey(
        JenisSanksi,
        on_delete=models.PROTECT,
        related_name="sanksi_tercatat",
    )
    dicatat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sanksi_keterlambatan_dicatat",
    )
    keterangan = models.TextField(blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "sanksi akademik tercatat"
        verbose_name_plural = "sanksi akademik tercatat"
        ordering = ["-dibuat_pada", "-id"]

    def __str__(self):
        return f"{self.jenis_sanksi.nama} · catatan #{self.catatan_id}"
