from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Jejak perubahan data akademik (BR-10). Hanya boleh dibuat, tidak pernah diubah."""

    class Aksi(models.TextChoices):
        TAMBAH = "tambah", "Tambah"
        UBAH = "ubah", "Ubah"
        HAPUS = "hapus", "Hapus"
        RESET_PASSWORD = "reset_password", "Reset password"

    aktor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    # Salinan identifier agar log tetap bermakna bila akun aktor kelak dihapus.
    # Kosong bila perubahan berasal dari perintah baris perintah (bukan admin).
    aktor_identifier = models.CharField(max_length=30, blank=True)
    aksi = models.CharField(max_length=20, choices=Aksi.choices)
    objek_tipe = models.CharField(max_length=100)
    objek_id = models.CharField(max_length=64)
    objek_repr = models.CharField(max_length=255, blank=True)
    sebelum = models.JSONField(null=True, blank=True)
    sesudah = models.JSONField(null=True, blank=True)
    keterangan = models.CharField(max_length=255, blank=True)
    waktu = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "audit log"
        verbose_name_plural = "audit log"
        ordering = ["-waktu", "-id"]
        indexes = [models.Index(fields=["objek_tipe", "objek_id"])]

    def __str__(self):
        return f"{self.waktu:%Y-%m-%d %H:%M} {self.aksi} {self.objek_tipe}#{self.objek_id}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("AuditLog tidak dapat diubah setelah dibuat.")
        super().save(*args, **kwargs)