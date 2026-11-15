from django.db import models


class HalamanBantuan(models.Model):
    judul = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    ringkasan = models.CharField(max_length=300, blank=True)
    konten = models.TextField()
    urutan = models.PositiveSmallIntegerField(default=0)
    aktif = models.BooleanField(default=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "halaman bantuan"
        verbose_name_plural = "halaman bantuan"
        ordering = ["urutan", "judul", "id"]

    def __str__(self):
        return self.judul
