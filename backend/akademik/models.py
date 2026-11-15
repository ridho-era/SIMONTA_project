from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum

from accounts.models import Role

BOBOT_TOTAL = Decimal("100")

# Catatan tentang kolom slot_*: MySQL tidak mendukung unique index bersyarat. Kolom
# slot bernilai True bila baris "aktif/utama" dan NULL bila tidak. NULL tidak dianggap
# sama oleh unique index, jadi hanya satu baris True yang bisa ada per kelompok.
# Nilai slot dihitung otomatis di save() dan tidak tampil di form.


class ProgramStudi(models.Model):
    nama = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = "program studi"
        verbose_name_plural = "program studi"
        ordering = ["nama"]

    def __str__(self):
        return self.nama


class PeriodeAkademik(models.Model):
    label = models.CharField(max_length=50, unique=True)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    aktif = models.BooleanField(default=False)
    slot_aktif = models.BooleanField(
        null=True, blank=True, unique=True, default=None, editable=False
    )

    class Meta:
        verbose_name = "periode akademik"
        verbose_name_plural = "periode akademik"
        ordering = ["-tanggal_mulai"]

    def __str__(self):
        return self.label

    @classmethod
    def aktif_sekarang(cls):
        return cls.objects.filter(aktif=True).first()

    def clean(self):
        if (
            self.tanggal_mulai
            and self.tanggal_selesai
            and self.tanggal_selesai < self.tanggal_mulai
        ):
            raise ValidationError(
                {"tanggal_selesai": "Tanggal selesai tidak boleh sebelum tanggal mulai."}
            )
        if self.aktif:
            lain = PeriodeAkademik.objects.filter(aktif=True).exclude(pk=self.pk).first()
            if lain:
                raise ValidationError(
                    {
                        "aktif": (
                            f"Periode '{lain.label}' masih aktif. Nonaktifkan dahulu "
                            "sebelum mengaktifkan periode lain."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.slot_aktif = True if self.aktif else None
        super().save(*args, **kwargs)


class TugasAkhir(models.Model):
    class Status(models.TextChoices):
        AKTIF = "aktif", "Aktif"
        SELESAI = "selesai", "Selesai"
        DIBATALKAN = "dibatalkan", "Dibatalkan"

    mahasiswa = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tugas_akhir",
        limit_choices_to={"role": Role.MAHASISWA},
    )
    periode = models.ForeignKey(
        PeriodeAkademik, on_delete=models.PROTECT, related_name="tugas_akhir"
    )
    judul = models.CharField(max_length=500)
    jenis_penelitian = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AKTIF)
    slot_aktif = models.BooleanField(null=True, blank=True, default=None, editable=False)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "tugas akhir"
        verbose_name_plural = "tugas akhir"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["mahasiswa", "slot_aktif"], name="uniq_ta_aktif_per_mahasiswa"
            )
        ]

    def __str__(self):
        return f"{self.mahasiswa.identifier} - {self.judul[:50]}"

    def clean(self):
        if self.status == self.Status.AKTIF and self.mahasiswa_id:
            ada = (
                TugasAkhir.objects.filter(
                    mahasiswa_id=self.mahasiswa_id, status=self.Status.AKTIF
                )
                .exclude(pk=self.pk)
                .exists()
            )
            if ada:
                raise ValidationError(
                    {
                        "status": (
                            "Mahasiswa ini sudah memiliki tugas akhir aktif. Ubah status "
                            "tugas akhir yang lama terlebih dahulu."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.slot_aktif = True if self.status == self.Status.AKTIF else None
        super().save(*args, **kwargs)


class Penugasan(models.Model):
    class Peran(models.TextChoices):
        UTAMA = "utama", "Pembimbing utama"
        PENDAMPING = "pendamping", "Pembimbing pendamping"
        PENGUJI = "penguji", "Penguji"

    tugas_akhir = models.ForeignKey(
        TugasAkhir, on_delete=models.CASCADE, related_name="penugasan"
    )
    dosen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="penugasan_dosen",
        limit_choices_to={"role": Role.DOSEN},
    )
    peran = models.CharField(max_length=12, choices=Peran.choices)
    slot_utama = models.BooleanField(null=True, blank=True, default=None, editable=False)

    class Meta:
        verbose_name = "penugasan"
        verbose_name_plural = "penugasan"
        constraints = [
            # Satu dosen punya satu peran per TA (juga menjamin satu percakapan per pasangan, BR-08).
            models.UniqueConstraint(
                fields=["tugas_akhir", "dosen"], name="uniq_penugasan_ta_dosen"
            ),
            models.UniqueConstraint(
                fields=["tugas_akhir", "slot_utama"], name="uniq_pembimbing_utama_per_ta"
            ),
        ]

    def __str__(self):
        return f"{self.dosen.identifier} ({self.get_peran_display()})"

    def save(self, *args, **kwargs):
        self.slot_utama = True if self.peran == self.Peran.UTAMA else None
        super().save(*args, **kwargs)


class MilestoneTemplate(models.Model):
    urutan = models.PositiveSmallIntegerField(unique=True, validators=[MinValueValidator(1)])
    nama = models.CharField(max_length=150)
    bobot = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(BOBOT_TOTAL)],
        help_text="Persen. Total bobot semua template aktif harus tepat 100.",
    )
    aktif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "template milestone"
        verbose_name_plural = "template milestone"
        ordering = ["urutan"]

    def __str__(self):
        return f"{self.urutan}. {self.nama}"

    @classmethod
    def total_bobot_aktif(cls):
        return cls.objects.filter(aktif=True).aggregate(total=Sum("bobot"))["total"] or Decimal("0")

    @classmethod
    def pastikan_total_valid(cls):
        """Dipanggil sebelum milestone dibuat untuk sebuah TA (BR-01).

        Raises ValidationError bila tidak ada template aktif atau total bobot bukan 100.
        """
        if not cls.objects.filter(aktif=True).exists():
            raise ValidationError("Belum ada template milestone aktif.")
        total = cls.total_bobot_aktif()
        if total != BOBOT_TOTAL:
            raise ValidationError(
                f"Total bobot template milestone aktif harus 100, saat ini {total}."
            )

    def clean(self):
        if not self.aktif or self.bobot is None:
            return
        lain = (
            MilestoneTemplate.objects.filter(aktif=True)
            .exclude(pk=self.pk)
            .aggregate(total=Sum("bobot"))["total"]
            or Decimal("0")
        )
        if lain + self.bobot > BOBOT_TOTAL:
            raise ValidationError(
                {
                    "bobot": (
                        "Total bobot template aktif tidak boleh melebihi 100. "
                        f"Sisa yang tersedia: {BOBOT_TOTAL - lain}."
                    )
                }
            )


class KonfigurasiDenda(models.Model):
    class Jenis(models.TextChoices):
        TELAT_REVISI = "telat_revisi", "Telat revisi"
        TELAT_BERKAS = "telat_berkas", "Telat pengumpulan berkas administrasi"

    periode = models.ForeignKey(
        PeriodeAkademik, on_delete=models.PROTECT, related_name="konfigurasi_denda"
    )
    jenis = models.CharField(max_length=12, choices=Jenis.choices)
    tarif = models.PositiveIntegerField(help_text="Rupiah per hari yang dikenai.")
    toleransi_hari = models.PositiveSmallIntegerField(default=0)
    batas_per_catatan = models.PositiveIntegerField(
        help_text="Batas nominal (Rupiah) untuk satu catatan keterlambatan."
    )
    label_simulasi = models.BooleanField(
        default=True,
        help_text='Menampilkan label "Simulasi: bukan kebijakan resmi kampus".',
    )

    class Meta:
        verbose_name = "konfigurasi denda"
        verbose_name_plural = "konfigurasi denda"
        ordering = ["-periode__tanggal_mulai", "jenis"]
        constraints = [
            models.UniqueConstraint(
                fields=["periode", "jenis"], name="uniq_konfigurasi_denda_periode_jenis"
            )
        ]

    def __str__(self):
        return f"{self.periode.label} - {self.get_jenis_display()}"


class JenisSanksi(models.Model):
    nama = models.CharField(max_length=150, unique=True)
    aktif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "jenis sanksi"
        verbose_name_plural = "jenis sanksi"
        ordering = ["nama"]

    def __str__(self):
        return self.nama