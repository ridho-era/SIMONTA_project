# Generated for T2.3: notification center, preferences, and idempotent reminders.
import datetime

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("milestone", "0001_initial"),
        ("notifikasi", "0002_alter_notifikasi_jenis"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notifikasi",
            name="jenis",
            field=models.CharField(
                choices=[
                    ("review_terbit", "Review terbit"),
                    ("milestone_diverifikasi", "Milestone diverifikasi"),
                    ("milestone_target", "Target milestone diubah"),
                    ("tenggat_terlewat", "Tenggat terlewat"),
                    ("pengingat", "Pengingat deadline"),
                    ("ringkasan_mingguan", "Ringkasan mingguan"),
                    ("jadwal_disetujui", "Jadwal disetujui"),
                    ("jadwal_ditolak", "Jadwal ditolak"),
                    ("jadwal_dibatalkan", "Jadwal dibatalkan"),
                    ("jadwal_diusulkan", "Waktu bimbingan diusulkan"),
                    ("permohonan_jadwal", "Permohonan jadwal"),
                    ("keputusan_keberatan", "Keputusan keberatan"),
                    ("dokumen_baru", "Dokumen baru"),
                    ("pesan_baru", "Pesan baru"),
                ],
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="notifikasi",
            name="kunci_idempoten",
            field=models.CharField(blank=True, max_length=180, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="notifikasi",
            name="email_dikirim_pada",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notifikasi",
            name="tampil_di_aplikasi",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="PengaturanNotifikasi",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pengingat_aktif", models.BooleanField(default=True)),
                ("h_minus_7", models.BooleanField(default=True)),
                ("h_minus_3", models.BooleanField(default=True)),
                ("h_minus_1", models.BooleanField(default=True)),
                ("kanal_aplikasi", models.BooleanField(default=True)),
                ("kanal_email", models.BooleanField(default=False)),
                ("ringkasan_mingguan", models.BooleanField(default=False)),
                ("dokumen_feedback_aktif", models.BooleanField(default=True)),
                ("jadwal_bimbingan_aktif", models.BooleanField(default=True)),
                ("jam_kirim", models.TimeField(default=datetime.time(8, 0))),
                ("zona_waktu", models.CharField(choices=[("Asia/Jakarta", "WIB — Asia/Jakarta")], default="Asia/Jakarta", max_length=32)),
                ("dibuat_pada", models.DateTimeField(auto_now_add=True)),
                ("diubah_pada", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="pengaturan_notifikasi", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "pengaturan notifikasi",
                "verbose_name_plural": "pengaturan notifikasi",
            },
        ),
        migrations.CreateModel(
            name="PengingatTerjadwal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("offset_hari", models.PositiveSmallIntegerField(choices=[(7, "H-7"), (3, "H-3"), (1, "H-1")])),
                ("tanggal_target", models.DateField()),
                ("jadwal_kirim", models.DateTimeField(db_index=True)),
                ("status", models.CharField(choices=[("terjadwal", "Terjadwal"), ("terkirim", "Terkirim"), ("dibatalkan", "Dibatalkan")], db_index=True, default="terjadwal", max_length=12)),
                ("dikirim_pada", models.DateTimeField(blank=True, null=True)),
                ("dibuat_pada", models.DateTimeField(auto_now_add=True)),
                ("diubah_pada", models.DateTimeField(auto_now=True)),
                ("milestone", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pengingat_terjadwal", to="milestone.milestone")),
                ("notifikasi", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pengingat_terjadwal", to="notifikasi.notifikasi")),
                ("pengguna", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pengingat_terjadwal", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "pengingat terjadwal",
                "verbose_name_plural": "pengingat terjadwal",
                "ordering": ["jadwal_kirim", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="pengingatterjadwal",
            constraint=models.UniqueConstraint(fields=("pengguna", "milestone", "offset_hari", "tanggal_target"), name="uniq_pengguna_ms_offset_target"),
        ),
        migrations.AddIndex(
            model_name="pengingatterjadwal",
            index=models.Index(fields=["status", "jadwal_kirim"], name="idx_pengingat_tempo"),
        ),
    ]
