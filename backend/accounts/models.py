import os
import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from .managers import UserManager


class Role(models.TextChoices):
    MAHASISWA = "mahasiswa", "Mahasiswa"
    DOSEN = "dosen", "Dosen"
    ADMIN = "admin", "Admin Prodi"


identifier_validator = RegexValidator(
    regex=r"^[A-Za-z0-9._-]+$",
    message="Hanya boleh huruf, angka, titik, garis bawah, dan tanda minus.",
)


def foto_upload_path(instance, filename):
    """Nama berkas diacak agar tidak membocorkan identitas dan tidak bentrok."""
    ext = os.path.splitext(filename)[1].lower()
    return f"foto_profil/{uuid.uuid4().hex}{ext}"


class User(AbstractBaseUser, PermissionsMixin):
    identifier = models.CharField(
        "identifier (NPM/NIP)",
        max_length=30,
        unique=True,
        validators=[identifier_validator],
        error_messages={"unique": "Identifier ini sudah terdaftar."},
    )
    role = models.CharField("role", max_length=10, choices=Role.choices)
    nama_lengkap = models.CharField("nama lengkap", max_length=150)
    gelar = models.CharField("gelar", max_length=100, blank=True)
    program_studi = models.ForeignKey(
        "akademik.ProgramStudi",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pengguna",
        verbose_name="program studi",
    )
    email_akademik = models.EmailField(
        "email akademik", null=True, blank=True, unique=True
    )
    telepon = models.CharField("telepon", max_length=20, blank=True)
    foto = models.ImageField("foto", upload_to=foto_upload_path, null=True, blank=True)
    is_active = models.BooleanField("aktif", default=True)
    is_staff = models.BooleanField("akses Django admin", default=False)
    must_change_password = models.BooleanField("wajib ganti password", default=False)
    date_joined = models.DateTimeField("tanggal dibuat", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "identifier"
    REQUIRED_FIELDS = ["nama_lengkap"]

    class Meta:
        verbose_name = "pengguna"
        verbose_name_plural = "pengguna"
        ordering = ["identifier"]
        indexes = [models.Index(fields=["role"])]

    def __str__(self):
        return f"{self.identifier} - {self.nama_lengkap}"

    def get_full_name(self):
        return self.nama_lengkap

    def get_short_name(self):
        return self.nama_lengkap

    def save(self, *args, **kwargs):
        # Email kosong disimpan sebagai NULL agar unique tidak bentrok antar akun tanpa email.
        self.email_akademik = self.email_akademik or None
        # Admin Prodi harus dapat masuk ke Django admin.
        if self.role == Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)