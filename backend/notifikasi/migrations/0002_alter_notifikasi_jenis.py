# Add schedule notification labels to the existing choices. The database column
# remains VARCHAR(30); this migration updates Django's migration state as well.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifikasi", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="notifikasi",
            name="jenis",
            field=models.CharField(
                max_length=30,
                choices=[
                    ("review_terbit", "Review terbit"),
                    ("milestone_diverifikasi", "Milestone diverifikasi"),
                    ("milestone_target", "Target milestone diubah"),
                    ("tenggat_terlewat", "Tenggat terlewat"),
                    ("pengingat", "Pengingat deadline"),
                    ("jadwal_disetujui", "Jadwal disetujui"),
                    ("jadwal_ditolak", "Jadwal ditolak"),
                    ("jadwal_dibatalkan", "Jadwal dibatalkan"),
                    ("jadwal_diusulkan", "Waktu bimbingan diusulkan"),
                    ("permohonan_jadwal", "Permohonan jadwal"),
                    ("keputusan_keberatan", "Keputusan keberatan"),
                    ("dokumen_baru", "Dokumen baru"),
                    ("pesan_baru", "Pesan baru"),
                ],
            ),
        ),
    ]
