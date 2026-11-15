from datetime import date

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Role, User

from .models import PeriodeAkademik

URL = "/api/v1/periode/aktif/"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PeriodeAktifApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            "TEST-MHS-001", "Sandi-Uji-12345!", role=Role.MAHASISWA, nama_lengkap="Mahasiswa Uji Palsu"
        )

    def buat(self, label, aktif):
        periode = PeriodeAkademik(
            label=label,
            tanggal_mulai=date(2030, 1, 1),
            tanggal_selesai=date(2030, 6, 30),
            aktif=aktif,
        )
        periode.save()
        return periode

    def test_butuh_login(self):
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_tanpa_periode_aktif_mengembalikan_null(self):
        self.buat("Periode Uji Nonaktif", aktif=False)
        self.client.force_login(self.user)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"periode": None})

    def test_mengembalikan_periode_aktif(self):
        self.buat("Periode Uji Nonaktif", aktif=False)
        aktif = self.buat("Periode Uji Aktif", aktif=True)
        self.client.force_login(self.user)
        body = self.client.get(URL).json()["periode"]
        self.assertEqual(body["id"], aktif.pk)
        self.assertEqual(body["label"], "Periode Uji Aktif")
        self.assertEqual(body["tanggal_mulai"], "2030-01-01")
        self.assertEqual(body["tanggal_selesai"], "2030-06-30")