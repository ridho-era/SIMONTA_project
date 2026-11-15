from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Role, User

from .models import Notifikasi
from .services import notify


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class NotifyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "TEST-MHS-001", "Sandi-Uji-12345!", role=Role.MAHASISWA, nama_lengkap="Mahasiswa Uji Palsu"
        )

    def test_notify_membuat_notifikasi_belum_dibaca(self):
        n = notify(self.user, Notifikasi.Jenis.PENGINGAT, "Judul uji", "Isi uji", "/mahasiswa/notifikasi")
        n.refresh_from_db()
        self.assertEqual(n.user, self.user)
        self.assertEqual(n.jenis, "pengingat")
        self.assertEqual(n.tautan, "/mahasiswa/notifikasi")
        self.assertIsNone(n.dibaca_pada)

    def test_jenis_tidak_dikenal_ditolak(self):
        with self.assertRaises(ValueError):
            notify(self.user, "jenis_ngawur", "Judul uji")
        self.assertEqual(Notifikasi.objects.count(), 0)

# Tes integrasi T2.3: jadwal pengingat, idempotensi, dan zona waktu WIB.
from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone as django_timezone

from akademik.models import MilestoneTemplate, Penugasan, PeriodeAkademik, TugasAkhir
from milestone.services import buat_milestone_untuk_ta
from .models import PengaturanNotifikasi, PengingatTerjadwal
from .services import sinkronkan_pengingat_ta, waktu_kirim
from .tasks import kirim_pengingat_jatuh_tempo, kirim_peringatan_tenggat


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PengingatOtomatisTests(TestCase):
    def setUp(self):
        from decimal import Decimal

        self.mhs = User.objects.create_user(
            "TEST-T23-MHS", "Sandi-Uji-12345!", role=Role.MAHASISWA, nama_lengkap="Mahasiswa Pengingat Uji"
        )
        self.dosen = User.objects.create_user(
            "TEST-T23-DSN", "Sandi-Uji-12345!", role=Role.DOSEN, nama_lengkap="Dosen Pengingat Uji"
        )
        self.periode = PeriodeAkademik.objects.create(
            label="Periode Pengingat Uji",
            tanggal_mulai=date(2030, 1, 1),
            tanggal_selesai=date(2030, 6, 30),
        )
        for urutan, bobot in enumerate(("30", "30", "40"), start=1):
            MilestoneTemplate.objects.create(urutan=urutan, nama=f"Tahap Pengingat {urutan}", bobot=Decimal(bobot))
        self.ta = TugasAkhir.objects.create(
            mahasiswa=self.mhs, periode=self.periode, judul="Tugas Akhir Uji Pengingat"
        )
        Penugasan.objects.create(tugas_akhir=self.ta, dosen=self.dosen, peran=Penugasan.Peran.UTAMA)
        buat_milestone_untuk_ta(self.ta)
        self.ms = self.ta.milestone.order_by("urutan").first()
        self.target_awal = django_timezone.localdate() + timedelta(days=20)
        self.ms.target = self.target_awal
        self.ms.save(update_fields=["target"])

    def test_pengingat_tidak_ganda_saat_task_dijalankan_dua_kali(self):
        sinkronkan_pengingat_ta(self.ta.pk, pengguna=self.mhs)
        reminder = PengingatTerjadwal.objects.get(pengguna=self.mhs, milestone=self.ms, offset_hari=7)
        reminder.jadwal_kirim = django_timezone.now() - timedelta(minutes=1)
        reminder.save(update_fields=["jadwal_kirim"])

        pertama = kirim_pengingat_jatuh_tempo.run()
        kedua = kirim_pengingat_jatuh_tempo.run()

        reminder.refresh_from_db()
        self.assertEqual(pertama["terkirim"], 1)
        self.assertEqual(kedua["terkirim"], 0)
        self.assertEqual(reminder.status, PengingatTerjadwal.Status.TERKIRIM)
        self.assertEqual(
            Notifikasi.objects.filter(kunci_idempoten=f"pengingat-terjadwal:{reminder.pk}").count(),
            1,
        )

    def test_pengingat_dibatalkan_jika_dosen_tidak_lagi_membimbing(self):
        sinkronkan_pengingat_ta(self.ta.pk)
        reminder = PengingatTerjadwal.objects.get(
            pengguna=self.dosen, milestone=self.ms, offset_hari=7
        )
        reminder.jadwal_kirim = django_timezone.now() - timedelta(minutes=1)
        reminder.save(update_fields=["jadwal_kirim"])
        Penugasan.objects.filter(tugas_akhir=self.ta, dosen=self.dosen).delete()

        hasil = kirim_pengingat_jatuh_tempo.run()

        reminder.refresh_from_db()
        self.assertEqual(hasil["terkirim"], 0)
        self.assertEqual(reminder.status, PengingatTerjadwal.Status.DIBATALKAN)
        self.assertEqual(
            Notifikasi.objects.filter(kunci_idempoten=f"pengingat-terjadwal:{reminder.pk}").count(),
            0,
        )

    def test_pengingat_dibatalkan_jika_semua_kanal_dimatikan(self):
        sinkronkan_pengingat_ta(self.ta.pk, pengguna=self.mhs)
        reminder = PengingatTerjadwal.objects.get(
            pengguna=self.mhs, milestone=self.ms, offset_hari=7
        )
        reminder.jadwal_kirim = django_timezone.now() - timedelta(minutes=1)
        reminder.save(update_fields=["jadwal_kirim"])
        pref = PengaturanNotifikasi.objects.get(user=self.mhs)
        pref.kanal_aplikasi = False
        pref.kanal_email = False
        pref.save(update_fields=["kanal_aplikasi", "kanal_email", "diubah_pada"])

        hasil = kirim_pengingat_jatuh_tempo.run()

        reminder.refresh_from_db()
        self.assertEqual(hasil["terkirim"], 0)
        self.assertEqual(reminder.status, PengingatTerjadwal.Status.DIBATALKAN)

    def test_perubahan_target_membatalkan_jadwal_lama_dan_membuat_jadwal_baru(self):
        sinkronkan_pengingat_ta(self.ta.pk, pengguna=self.mhs)
        awal = PengingatTerjadwal.objects.filter(pengguna=self.mhs, milestone=self.ms)
        self.assertEqual(awal.filter(status=PengingatTerjadwal.Status.TERJADWAL).count(), 3)

        target_baru = self.target_awal + timedelta(days=10)
        from milestone.services import tetapkan_target

        tetapkan_target(self.ms, target_baru, self.dosen)
        # Pemanggilan ulang sinkronisasi tidak boleh membuat jadwal tambahan.
        sinkronkan_pengingat_ta(self.ta.pk, pengguna=self.mhs)
        sinkronkan_pengingat_ta(self.ta.pk, pengguna=self.mhs)

        self.assertEqual(
            PengingatTerjadwal.objects.filter(
                pengguna=self.mhs, milestone=self.ms, tanggal_target=self.target_awal,
                status=PengingatTerjadwal.Status.DIBATALKAN,
            ).count(),
            3,
        )
        self.assertEqual(
            PengingatTerjadwal.objects.filter(
                pengguna=self.mhs, milestone=self.ms, tanggal_target=target_baru,
                status=PengingatTerjadwal.Status.TERJADWAL,
            ).count(),
            3,
        )
        self.assertEqual(
            PengingatTerjadwal.objects.filter(pengguna=self.mhs, milestone=self.ms).count(),
            6,
        )

    def test_milestone_diverifikasi_membatalkan_pengingat_tertunda(self):
        sinkronkan_pengingat_ta(self.ta.pk, pengguna=self.mhs)
        from milestone.services import verifikasi

        verifikasi(self.ms, 80, self.dosen)
        self.assertEqual(
            PengingatTerjadwal.objects.filter(
                pengguna=self.mhs, milestone=self.ms, status=PengingatTerjadwal.Status.DIBATALKAN
            ).count(),
            3,
        )

    def test_tenggat_terlewat_terpisah_dan_tidak_ganda(self):
        self.ms.target = django_timezone.localdate() - timedelta(days=1)
        self.ms.save(update_fields=["target"])

        pertama = kirim_peringatan_tenggat.run()
        kedua = kirim_peringatan_tenggat.run()

        self.assertEqual(pertama["peringatan_dibuat"], 2)
        self.assertEqual(kedua["peringatan_dibuat"], 0)
        self.assertEqual(
            Notifikasi.objects.filter(jenis=Notifikasi.Jenis.TENGGAT_TERLEWAT).count(),
            2,
        )
        self.assertEqual(Notifikasi.objects.filter(jenis=Notifikasi.Jenis.PENGINGAT).count(), 0)

    def test_waktu_pengiriman_mengikuti_jam_wib(self):
        target = date(2027, 4, 20)
        terjadwal = waktu_kirim(target, 7, time(8, 15), "Asia/Jakarta")
        lokal = terjadwal.astimezone(ZoneInfo("Asia/Jakarta"))
        self.assertEqual(lokal.date(), target - timedelta(days=7))
        self.assertEqual(lokal.time().replace(tzinfo=None), time(8, 15))
        self.assertEqual(lokal.utcoffset(), timedelta(hours=7))

    def test_pratinjau_menghitung_jadwal_dari_target_milestone_aktif(self):
        client = APIClient()
        client.force_login(self.mhs)
        respons = client.get("/api/v1/notifikasi/pratinjau-pengingat/")
        self.assertEqual(respons.status_code, 200)
        hasil = respons.json()["hasil"]
        self.assertEqual({item["offset_hari"] for item in hasil}, {7, 3, 1})
        self.assertTrue(all(item["target"] == self.target_awal.isoformat() for item in hasil))
        self.assertTrue(all(item["zona_waktu"] == "Asia/Jakarta" for item in hasil))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class NotifikasiApiT23Tests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            "TEST-T23-API", "Sandi-Uji-12345!", role=Role.MAHASISWA, nama_lengkap="Mahasiswa API Uji"
        )
        self.client.force_login(self.user)

    def test_pusat_notifikasi_tandai_dibaca_dan_badge(self):
        item = notify(self.user, Notifikasi.Jenis.PENGINGAT, "Notifikasi Uji", "Isi uji")
        daftar = self.client.get("/api/v1/notifikasi/")
        self.assertEqual(daftar.status_code, 200)
        self.assertEqual(daftar.json()["jumlah_belum_dibaca"], 1)
        dibaca = self.client.post(f"/api/v1/notifikasi/{item.pk}/dibaca/")
        self.assertEqual(dibaca.status_code, 200)
        badge = self.client.get("/api/v1/notifikasi/jumlah-belum-dibaca/")
        self.assertEqual(badge.json()["jumlah_belum_dibaca"], 0)

        notify(self.user, Notifikasi.Jenis.PENGINGAT, "Notifikasi Uji Kedua", "Isi kedua")
        semua = self.client.post("/api/v1/notifikasi/dibaca-semua/")
        self.assertEqual(semua.status_code, 200)
        self.assertEqual(semua.json()["jumlah_diperbarui"], 1)

    def test_pengaturan_dan_pulihkan_default(self):
        awal = self.client.get("/api/v1/notifikasi/pengaturan/")
        self.assertEqual(awal.status_code, 200)
        simpan = self.client.patch(
            "/api/v1/notifikasi/pengaturan/",
            {"h_minus_7": False, "jam_kirim": "09:30", "zona_waktu": "Asia/Jakarta"},
            format="json",
        )
        self.assertEqual(simpan.status_code, 200)
        self.assertFalse(simpan.json()["h_minus_7"])
        pulih = self.client.post("/api/v1/notifikasi/pengaturan/pulihkan-default/")
        self.assertEqual(pulih.status_code, 200)
        self.assertTrue(pulih.json()["h_minus_7"])
        self.assertEqual(pulih.json()["jam_kirim"], "08:00:00")
