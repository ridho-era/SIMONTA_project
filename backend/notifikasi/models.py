from datetime import time

from django.conf import settings
from django.db import models


class Notifikasi(models.Model):
    class Jenis(models.TextChoices):
        REVIEW_TERBIT = "review_terbit", "Review terbit"
        MILESTONE_DIVERIFIKASI = "milestone_diverifikasi", "Milestone diverifikasi"
        MILESTONE_TARGET = "milestone_target", "Target milestone diubah"
        TENGGAT_TERLEWAT = "tenggat_terlewat", "Tenggat terlewat"
        PENGINGAT = "pengingat", "Pengingat deadline"
        RINGKASAN_MINGGUAN = "ringkasan_mingguan", "Ringkasan mingguan"
        JADWAL_DISETUJUI = "jadwal_disetujui", "Jadwal disetujui"
        JADWAL_DITOLAK = "jadwal_ditolak", "Jadwal ditolak"
        JADWAL_DIBATALKAN = "jadwal_dibatalkan", "Jadwal dibatalkan"
        JADWAL_DIUSULKAN = "jadwal_diusulkan", "Waktu bimbingan diusulkan"
        PERMOHONAN_JADWAL = "permohonan_jadwal", "Permohonan jadwal"
        KEPUTUSAN_KEBERATAN = "keputusan_keberatan", "Keputusan keberatan"
        DOKUMEN_BARU = "dokumen_baru", "Dokumen baru"
        PESAN_BARU = "pesan_baru", "Pesan baru"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifikasi"
    )
    jenis = models.CharField(max_length=30, choices=Jenis.choices)
    judul = models.CharField(max_length=200)
    isi = models.TextField(blank=True)
    tautan = models.CharField(max_length=255, blank=True)
    dibaca_pada = models.DateTimeField(null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True, db_index=True)
    tampil_di_aplikasi = models.BooleanField(default=True)
    # Null untuk notifikasi biasa; terisi untuk event yang perlu dijamin idempoten.
    kunci_idempoten = models.CharField(max_length=180, null=True, blank=True, unique=True)
    email_dikirim_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "notifikasi"
        verbose_name_plural = "notifikasi"
        ordering = ["-dibuat_pada", "-id"]
        indexes = [models.Index(fields=["user", "dibaca_pada"])]

    def __str__(self):
        return f"{self.jenis}: {self.judul}"


class PengaturanNotifikasi(models.Model):
    """Preferensi kanal dan jam pengingat milik satu akun portal."""

    ZONA_WIB = "Asia/Jakarta"
    ZONA_CHOICES = [(ZONA_WIB, "WIB — Asia/Jakarta")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pengaturan_notifikasi",
    )
    pengingat_aktif = models.BooleanField(default=True)
    h_minus_7 = models.BooleanField(default=True)
    h_minus_3 = models.BooleanField(default=True)
    h_minus_1 = models.BooleanField(default=True)
    kanal_aplikasi = models.BooleanField(default=True)
    kanal_email = models.BooleanField(default=False)
    ringkasan_mingguan = models.BooleanField(default=False)
    # Preferensi tambahan khusus dosen pada F-16.
    dokumen_feedback_aktif = models.BooleanField(default=True)
    jadwal_bimbingan_aktif = models.BooleanField(default=True)
    jam_kirim = models.TimeField(default=time(8, 0))
    zona_waktu = models.CharField(max_length=32, choices=ZONA_CHOICES, default=ZONA_WIB)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "pengaturan notifikasi"
        verbose_name_plural = "pengaturan notifikasi"

    def __str__(self):
        return f"Pengaturan notifikasi: {self.user}"


class PengingatTerjadwal(models.Model):
    class Status(models.TextChoices):
        TERJADWAL = "terjadwal", "Terjadwal"
        TERKIRIM = "terkirim", "Terkirim"
        DIBATALKAN = "dibatalkan", "Dibatalkan"

    pengguna = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pengingat_terjadwal",
    )
    milestone = models.ForeignKey(
        "milestone.Milestone",
        on_delete=models.CASCADE,
        related_name="pengingat_terjadwal",
    )
    offset_hari = models.PositiveSmallIntegerField(choices=[(7, "H-7"), (3, "H-3"), (1, "H-1")])
    tanggal_target = models.DateField()
    jadwal_kirim = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.TERJADWAL, db_index=True
    )
    notifikasi = models.OneToOneField(
        Notifikasi,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengingat_terjadwal",
    )
    dikirim_pada = models.DateTimeField(null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "pengingat terjadwal"
        verbose_name_plural = "pengingat terjadwal"
        ordering = ["jadwal_kirim", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["pengguna", "milestone", "offset_hari", "tanggal_target"],
                name="uniq_pengguna_ms_offset_target",
            )
        ]
        indexes = [models.Index(fields=["status", "jadwal_kirim"], name="idx_pengingat_tempo")]

    def __str__(self):
        return f"{self.pengguna_id}: milestone {self.milestone_id} H-{self.offset_hari}"
