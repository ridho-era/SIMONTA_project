from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from dokumen.models import DokumenVersi


class Review(models.Model):
    """Feedback pembimbing atas satu versi dokumen.

    Satu pemberi hanya boleh memiliki satu draf aktif untuk satu versi. Setelah
    terbit, slot draf dilepas sehingga koreksi dapat dibuat sebagai review baru.
    Nilai NULL pada slot_draf memungkinkan beberapa review terbit tersimpan.
    """

    class Rekomendasi(models.TextChoices):
        PERLU_REVISI = "perlu_revisi", "Perlu revisi"
        DISETUJUI = "disetujui", "Disetujui"

    class Status(models.TextChoices):
        DRAF = "draf", "Draf"
        TERBIT = "terbit", "Terbit"

    versi = models.ForeignKey(
        DokumenVersi, on_delete=models.PROTECT, related_name="reviews"
    )
    pemberi = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="review_dokumen"
    )
    bagian = models.TextField(blank=True, help_text="Bagian atau halaman yang direview.")
    komentar = models.TextField(blank=True, help_text="Komentar dan arahan pembimbing.")
    nilai = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    rekomendasi = models.CharField(
        max_length=20, choices=Rekomendasi.choices, null=True, blank=True
    )
    tenggat_revisi = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAF)
    diterbitkan_pada = models.DateTimeField(null=True, blank=True)
    bagikan_catatan_awal = models.BooleanField(
        default=False,
        help_text="Hanya bagian dan komentar yang dibagikan kepada mahasiswa sebagai catatan awal.",
    )
    slot_draf = models.BooleanField(null=True, blank=True, default=True, editable=False)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "review dokumen"
        verbose_name_plural = "review dokumen"
        ordering = ["-diterbitkan_pada", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["versi", "pemberi", "slot_draf"],
                name="uniq_review_draf_versi_pemberi",
            ),
            models.CheckConstraint(
                check=Q(nilai__isnull=True) | Q(nilai__gte=0, nilai__lte=100),
                name="review_nilai_0_100",
            ),
        ]
        indexes = [models.Index(fields=["versi", "status"], name="review_ver_st_idx")]

    def __str__(self):
        return f"Review {self.versi} oleh {self.pemberi} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            status_lama = (
                type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
            )
            if status_lama == self.Status.TERBIT:
                raise ValueError("Review yang sudah diterbitkan tidak dapat diubah.")
        self.slot_draf = True if self.status == self.Status.DRAF else None
        if self.status == self.Status.TERBIT and self.diterbitkan_pada is None:
            self.diterbitkan_pada = timezone.now()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status == self.Status.TERBIT:
            raise ValueError("Review yang sudah diterbitkan tidak dapat dihapus.")
        return super().delete(*args, **kwargs)


class ChecklistRevisi(models.Model):
    """Catatan kerja pribadi mahasiswa untuk satu review yang sudah diterbitkan."""

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="checklist")
    mahasiswa = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="checklist_revisi"
    )
    catatan = models.CharField(max_length=1000)
    selesai = models.BooleanField(default=False)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "checklist revisi pribadi"
        verbose_name_plural = "checklist revisi pribadi"
        ordering = ["selesai", "dibuat_pada", "id"]
        indexes = [models.Index(fields=["mahasiswa", "review", "selesai"], name="checklist_mhs_rev_done_idx")]

    def __str__(self):
        return f"Checklist {self.mahasiswa_id} · review {self.review_id}"