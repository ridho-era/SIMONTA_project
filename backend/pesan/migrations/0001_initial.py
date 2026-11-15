# Generated for SIMONTA T2.2: Pesan pembimbing.
import pesan.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("akademik", "0001_initial"),
        ("dokumen", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Percakapan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dibuat_pada", models.DateTimeField(auto_now_add=True)),
                ("diubah_pada", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("dosen", models.ForeignKey(limit_choices_to={"role": "dosen"}, on_delete=django.db.models.deletion.PROTECT, related_name="percakapan_pembimbing", to=settings.AUTH_USER_MODEL)),
                ("tugas_akhir", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="percakapan", to="akademik.tugasakhir")),
            ],
            options={
                "verbose_name": "percakapan",
                "verbose_name_plural": "percakapan",
                "ordering": ["-diubah_pada", "-id"],
            },
        ),
        migrations.CreateModel(
            name="Pesan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("isi", models.TextField(blank=True, max_length=10000)),
                ("lampiran", models.FileField(blank=True, max_length=255, null=True, upload_to=pesan.models.lampiran_upload_path)),
                ("nama_lampiran", models.CharField(blank=True, max_length=255)),
                ("dibuat_pada", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("dibaca_pada", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("dokumen_versi", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pesan_terkait", to="dokumen.dokumenversi")),
                ("pengirim", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pesan_dikirim", to=settings.AUTH_USER_MODEL)),
                ("percakapan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pesan", to="pesan.percakapan")),
            ],
            options={
                "verbose_name": "pesan",
                "verbose_name_plural": "pesan",
                "ordering": ["dibuat_pada", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="percakapan",
            constraint=models.UniqueConstraint(fields=("tugas_akhir", "dosen"), name="uniq_percakapan_ta_dosen"),
        ),
        migrations.AddIndex(
            model_name="percakapan",
            index=models.Index(fields=["dosen", "diubah_pada"], name="pesan_dosen_diubah_idx"),
        ),
        migrations.AddIndex(
            model_name="pesan",
            index=models.Index(fields=["percakapan", "id"], name="pesan_thread_id_idx"),
        ),
        migrations.AddIndex(
            model_name="pesan",
            index=models.Index(fields=["percakapan", "dibaca_pada"], name="pesan_thread_read_idx"),
        ),
    ]
