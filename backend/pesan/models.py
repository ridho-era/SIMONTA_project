import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from akademik.models import TugasAkhir
from dokumen.models import DokumenVersi


def lampiran_upload_path(instance, filename):
    """Simpan lampiran dengan nama acak; nama asli disimpan terpisah."""
    ekstensi = os.path.splitext(filename)[1].lower()
    return f"pesan/{uuid.uuid4().hex}{ekstensi}"


class Percakapan(models.Model):
    """Satu thread untuk pasangan mahasiswa dan dosen pada satu Tugas Akhir."""

    tugas_akhir = models.ForeignKey(
        TugasAkhir, on_delete=models.CASCADE, related_name="percakapan"
    )
    dosen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="percakapan_pembimbing",
        limit_choices_to={"role": "dosen"},
    )
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diubah_pada = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "percakapan"
        verbose_name_plural = "percakapan"
        ordering = ["-diubah_pada", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["tugas_akhir", "dosen"], name="uniq_percakapan_ta_dosen"
            )
        ]
        indexes = [models.Index(fields=["dosen", "diubah_pada"], name="pesan_dosen_diubah_idx")]

    @property
    def mahasiswa(self):
        return self.tugas_akhir.mahasiswa

    def peserta(self, user):
        return user.pk in {self.tugas_akhir.mahasiswa_id, self.dosen_id}

    def lawan_bicara(self, user):
        if user.pk == self.tugas_akhir.mahasiswa_id:
            return self.dosen
        if user.pk == self.dosen_id:
            return self.tugas_akhir.mahasiswa
        return None

    def __str__(self):
        return f"{self.tugas_akhir.mahasiswa.identifier} ↔ {self.dosen.identifier}"


class Pesan(models.Model):
    percakapan = models.ForeignKey(
        Percakapan, on_delete=models.CASCADE, related_name="pesan"
    )
    pengirim = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pesan_dikirim"
    )
    isi = models.TextField(blank=True, max_length=10000)
    lampiran = models.FileField(
        upload_to=lampiran_upload_path, max_length=255, null=True, blank=True
    )
    nama_lampiran = models.CharField(max_length=255, blank=True)
    dokumen_versi = models.ForeignKey(
        DokumenVersi,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pesan_terkait",
    )
    dibuat_pada = models.DateTimeField(auto_now_add=True, db_index=True)
    dibaca_pada = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "pesan"
        verbose_name_plural = "pesan"
        ordering = ["dibuat_pada", "id"]
        indexes = [
            models.Index(fields=["percakapan", "id"], name="pesan_thread_id_idx"),
            models.Index(fields=["percakapan", "dibaca_pada"], name="pesan_thread_read_idx"),
        ]

    def __str__(self):
        return f"Pesan #{self.pk} – {self.pengirim.identifier}"

    def clean(self):
        if self.dokumen_versi_id and self.percakapan_id:
            ta_id = self.dokumen_versi.dokumen.milestone.tugas_akhir_id
            if ta_id != self.percakapan.tugas_akhir_id:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    {"dokumen_versi": "Dokumen harus berasal dari tugas akhir percakapan ini."}
                )
