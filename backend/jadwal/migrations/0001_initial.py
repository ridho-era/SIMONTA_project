# Generated for SIMONTA T2.1: Jadwal bimbingan.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("akademik", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Bimbingan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mulai", models.DateTimeField()),
                ("selesai", models.DateTimeField()),
                ("mode", models.CharField(choices=[("luring", "Luring"), ("daring", "Daring")], max_length=10)),
                ("lokasi_atau_tautan", models.CharField(blank=True, max_length=500)),
                ("agenda", models.TextField(blank=True, max_length=2000)),
                ("status", models.CharField(choices=[("menunggu_konfirmasi", "Menunggu Konfirmasi"), ("disetujui", "Disetujui"), ("ditolak", "Ditolak"), ("dibatalkan", "Dibatalkan"), ("selesai", "Selesai")], default="menunggu_konfirmasi", max_length=24)),
                ("alasan_penolakan", models.TextField(blank=True, max_length=2000)),
                ("dibuat_pada", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("diubah_pada", models.DateTimeField(auto_now=True)),
                ("dosen", models.ForeignKey(limit_choices_to={"role": "dosen"}, on_delete=django.db.models.deletion.PROTECT, related_name="jadwal_bimbingan", to=settings.AUTH_USER_MODEL)),
                ("menggantikan", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="permohonan_pengganti", to="jadwal.bimbingan")),
                ("tugas_akhir", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bimbingan", to="akademik.tugasakhir")),
            ],
            options={
                "verbose_name": "jadwal bimbingan",
                "verbose_name_plural": "jadwal bimbingan",
                "ordering": ["mulai", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="bimbingan",
            index=models.Index(fields=["dosen", "status", "mulai"], name="jadwal_dosen_status_mulai_idx"),
        ),
        migrations.AddIndex(
            model_name="bimbingan",
            index=models.Index(fields=["tugas_akhir", "status", "mulai"], name="jadwal_ta_status_mulai_idx"),
        ),
    ]
