import os
import uuid

from django.db import models

from milestone.models import Milestone


def berkas_upload_path(instance, filename):
    """Nama di storage diacak (uuid); nama asli tidak pernah dipakai sebagai path."""
    ekstensi = os.path.splitext(filename)[1].lower()
    return f"dokumen/{uuid.uuid4().hex}{ekstensi}"


class Dokumen(models.Model):
    """Wadah versi-versi berkas untuk satu milestone."""

    milestone = models.OneToOneField(Milestone, on_delete=models.PROTECT, related_name="dokumen")
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "dokumen"
        verbose_name_plural = "dokumen"

    def __str__(self):
        return f"Dokumen {self.milestone}"


class DokumenVersi(models.Model):
    class Status(models.TextChoices):
        MENUNGGU_REVIEW = "menunggu_review", "Menunggu Review"
        PERLU_REVISI = "perlu_revisi", "Perlu Revisi"
        DISETUJUI = "disetujui", "Disetujui"

    dokumen = models.ForeignKey(Dokumen, on_delete=models.PROTECT, related_name="versi")
    nomor_versi = models.PositiveIntegerField()
    berkas = models.FileField(upload_to=berkas_upload_path, max_length=255)
    nama_asli = models.CharField(max_length=255)
    halaman = models.PositiveIntegerField(null=True, blank=True, help_text="Hanya untuk PDF.")
    ukuran = models.PositiveBigIntegerField(help_text="Byte.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.MENUNGGU_REVIEW)
    catatan = models.TextField(blank=True)
    diunggah_pada = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "versi dokumen"
        verbose_name_plural = "versi dokumen"
        ordering = ["-diunggah_pada", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["dokumen", "nomor_versi"], name="uniq_versi_per_dokumen")
        ]

    def __str__(self):
        return f"{self.dokumen} v{self.nomor_versi}"

    def save(self, *args, **kwargs):
        # BR-04: versi tidak dapat diubah. Satu-satunya perubahan sah adalah status (review, T1.3).
        if not self._state.adding:
            kolom = kwargs.get("update_fields")
            if kolom is None or not set(kolom) <= {"status"}:
                raise ValueError("Versi dokumen tidak dapat diubah; hanya status yang boleh diperbarui.")
        super().save(*args, **kwargs)