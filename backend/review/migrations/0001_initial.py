# Generated for SIMONTA T1.3.
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("dokumen", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bagian", models.TextField(blank=True, help_text="Bagian atau halaman yang direview.")),
                ("komentar", models.TextField(blank=True, help_text="Komentar dan arahan pembimbing.")),
                (
                    "nilai",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
                    ),
                ),
                (
                    "rekomendasi",
                    models.CharField(
                        blank=True,
                        choices=[("perlu_revisi", "Perlu revisi"), ("disetujui", "Disetujui")],
                        max_length=20,
                        null=True,
                    ),
                ),
                ("tenggat_revisi", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("draf", "Draf"), ("terbit", "Terbit")], default="draf", max_length=10)),
                ("diterbitkan_pada", models.DateTimeField(blank=True, null=True)),
                (
                    "bagikan_catatan_awal",
                    models.BooleanField(
                        default=False,
                        help_text="Hanya bagian dan komentar yang dibagikan kepada mahasiswa sebagai catatan awal.",
                    ),
                ),
                ("slot_draf", models.BooleanField(blank=True, default=True, editable=False, null=True)),
                ("dibuat_pada", models.DateTimeField(auto_now_add=True)),
                ("diubah_pada", models.DateTimeField(auto_now=True)),
                (
                    "pemberi",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="review_dokumen", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "versi",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reviews", to="dokumen.dokumenversi"),
                ),
            ],
            options={
                "verbose_name": "review dokumen",
                "verbose_name_plural": "review dokumen",
                "ordering": ["-diterbitkan_pada", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ChecklistRevisi",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("catatan", models.CharField(max_length=1000)),
                ("selesai", models.BooleanField(default=False)),
                ("dibuat_pada", models.DateTimeField(auto_now_add=True)),
                ("diubah_pada", models.DateTimeField(auto_now=True)),
                (
                    "mahasiswa",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="checklist_revisi", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "review",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="checklist", to="review.review"),
                ),
            ],
            options={
                "verbose_name": "checklist revisi pribadi",
                "verbose_name_plural": "checklist revisi pribadi",
                "ordering": ["selesai", "dibuat_pada", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.UniqueConstraint(fields=("versi", "pemberi", "slot_draf"), name="uniq_review_draf_versi_pemberi"),
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.CheckConstraint(check=models.Q(nilai__isnull=True) | models.Q(nilai__gte=0, nilai__lte=100), name="review_nilai_0_100"),
        ),
        migrations.AddIndex(
            model_name="review",
            index=models.Index(fields=["versi", "status"], name="review_ver_st_idx"),
        ),
        migrations.AddIndex(
            model_name="checklistrevisi",
            index=models.Index(fields=["mahasiswa", "review", "selesai"], name="checklist_mhs_rev_done_idx"),
        ),
    ]