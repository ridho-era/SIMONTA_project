from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import HalamanBantuan

User = get_user_model()
PASSWORD = "Sandi-Uji-Bantuan-123!"
HELP_URL = "/api/v1/bantuan/"
FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class PusatBantuanApiTests(TestCase):
    def setUp(self):
        self.mahasiswa = User.objects.create_user(
            "TEST-BANTUAN-MHS", PASSWORD, role="mahasiswa", nama_lengkap="Mahasiswa Bantuan Uji"
        )
        self.admin = User.objects.create_user(
            "TEST-BANTUAN-ADM", PASSWORD, role="admin", nama_lengkap="Admin Bantuan Uji"
        )
        self.client = APIClient()

    def test_empty_state_api_mengembalikan_daftar_kosong(self):
        self.client.force_login(self.mahasiswa)
        response = self.client.get(HELP_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_hanya_halaman_aktif_yang_ditampilkan(self):
        aktif = HalamanBantuan.objects.create(
            judul="Panduan unggah dokumen uji", slug="panduan-unggah-uji",
            ringkasan="Ringkasan panduan uji", konten="Konten panduan uji.", aktif=True,
        )
        HalamanBantuan.objects.create(
            judul="Panduan nonaktif uji", slug="panduan-nonaktif-uji",
            konten="Konten nonaktif.", aktif=False,
        )
        self.client.force_login(self.mahasiswa)
        response = self.client.get(HELP_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["id"], aktif.pk)

    def test_endpoint_bantuan_memerlukan_peran_portal(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(HELP_URL).status_code, 403)
