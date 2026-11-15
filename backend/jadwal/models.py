from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from akademik.models import TugasAkhir


class Bimbingan(models.Model):
    class Mode(models.TextChoices):
        LURING = "luring", "Luring"
        DARING = "daring", "Daring"

    class Status(models.TextChoices):
        MENUNGGU_KONFIRMASI = "menunggu_konfirmasi", "Menunggu Konfirmasi"
        DISETUJUI = "disetujui", "Disetujui"
        DITOLAK = "ditolak", "Ditolak"
        DIBATALKAN = "dibatalkan", "Dibatalkan"
        SELESAI = "selesai", "Selesai"

    tugas_akhir = models.ForeignKey(
        TugasAkhir, on_delete=models.CASCADE, related_name="bimbingan"
    )
    dosen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="jadwal_bimbingan",
        limit_choices_to={"role": "dosen"},
    )
    mulai = models.DateTimeField()
    selesai = models.DateTimeField()
    mode = models.CharField(max_length=10, choices=Mode.choices)
    lokasi_atau_tautan = models.CharField(max_length=500, blank=True)
    agenda = models.TextField(blank=True, max_length=2000)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.MENUNGGU_KONFIRMASI,
    )
    menggantikan = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="permohonan_pengganti",
    )
    alasan_penolakan = models.TextField(blank=True, max_length=2000)
    dibuat_pada = models.DateTimeField(auto_now_add=True, db_index=True)
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "jadwal bimbingan"
        verbose_name_plural = "jadwal bimbingan"
        ordering = ["mulai", "id"]
        indexes = [
            models.Index(fields=["dosen", "status", "mulai"], name="jadwal_dosen_status_mulai_idx"),
            models.Index(fields=["tugas_akhir", "status", "mulai"], name="jadwal_ta_status_mulai_idx"),
        ]

    def __str__(self):
        return f"{self.tugas_akhir.mahasiswa.identifier} – {self.mulai:%Y-%m-%d %H:%M}"

    def clean(self):
        errors = {}
        if self.mulai and self.selesai:
            if self.selesai <= self.mulai:
                errors["selesai"] = "Jam selesai harus setelah jam mulai."
            if self.mulai < timezone.now():
                errors["mulai"] = "Jadwal tidak boleh berada di masa lalu."
        if errors:
            raise ValidationError(errors)
