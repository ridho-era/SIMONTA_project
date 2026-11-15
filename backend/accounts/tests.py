from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from .models import Role
from .permissions import IsAdminProdi, IsDosen, IsMahasiswa

User = get_user_model()

# Hasher cepat hanya untuk tes; hasher produksi (Argon2) diuji terpisah di HasherTests.
FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Semua data di bawah ini sintetis dan jelas palsu.
PASSWORD = "Sandi-Uji-12345!"
NEW_PASSWORD = "Sandi-Baru-67890?"
CSRF_URL = "/api/v1/auth/csrf/"
LOGIN_URL = "/api/v1/auth/login/"
LOGOUT_URL = "/api/v1/auth/logout/"
ME_URL = "/api/v1/auth/me/"
CHANGE_PASSWORD_URL = "/api/v1/auth/change-password/"


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class AuthTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.mahasiswa = User.objects.create_user(
            "TEST-MHS-001", PASSWORD, role=Role.MAHASISWA, nama_lengkap="Mahasiswa Uji Palsu"
        )
        self.dosen = User.objects.create_user(
            "TEST-DSN-001", PASSWORD, role=Role.DOSEN, nama_lengkap="Dosen Uji Palsu"
        )
        self.admin = User.objects.create_user(
            "TEST-ADM-001", PASSWORD, role=Role.ADMIN, nama_lengkap="Admin Uji Palsu"
        )

    def login(self, identifier="TEST-MHS-001", password=PASSWORD, tipe="mahasiswa", **extra):
        payload = {"identifier": identifier, "password": password, "tipe": tipe}
        payload.update(extra)
        return self.client.post(LOGIN_URL, payload, format="json")


class LoginTests(AuthTestBase):
    def test_login_mahasiswa_berhasil(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["identifier"], "TEST-MHS-001")
        self.assertEqual(body["role"], "mahasiswa")
        self.assertNotIn("password", body)
        self.assertEqual(self.client.get(ME_URL).status_code, 200)

    def test_login_dosen_berhasil(self):
        response = self.login(identifier="TEST-DSN-001", tipe="dosen")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "dosen")

    def test_salah_tipe_ditolak(self):
        kasus = [
            ("TEST-MHS-001", "dosen"),
            ("TEST-DSN-001", "mahasiswa"),
            ("TEST-ADM-001", "mahasiswa"),
            ("TEST-ADM-001", "dosen"),
        ]
        for identifier, tipe in kasus:
            with self.subTest(identifier=identifier, tipe=tipe):
                response = self.login(identifier=identifier, tipe=tipe)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(self.client.get(ME_URL).status_code, 403)

    def test_akun_nonaktif_ditolak(self):
        self.mahasiswa.is_active = False
        self.mahasiswa.save()
        response = self.login()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get(ME_URL).status_code, 403)

    def test_pesan_galat_generik_dan_sama(self):
        self.dosen.is_active = False
        self.dosen.save()
        respons = [
            self.login(password="password-salah"),
            self.login(identifier="TIDAK-ADA"),
            self.login(tipe="dosen"),
            self.login(identifier="TEST-DSN-001", tipe="dosen"),
        ]
        for response in respons:
            self.assertEqual(response.status_code, 401)
        self.assertEqual(len({r.json()["detail"] for r in respons}), 1)

    def test_lockout_setelah_5_gagal_per_akun_dan_ip(self):
        for _ in range(5):
            self.login(password="salah-total")
        response = self.login()  # password benar pun ditolak saat terkunci
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        self.assertEqual(self.client.get(ME_URL).status_code, 403)
        # Akun lain dari IP yang sama tidak ikut terkunci.
        lain = self.login(identifier="TEST-DSN-001", tipe="dosen")
        self.assertEqual(lain.status_code, 200)

    def test_empat_gagal_belum_terkunci(self):
        for _ in range(4):
            self.login(password="salah-total")
        self.assertEqual(self.login().status_code, 200)

    def test_ingat_saya_memperpanjang_sesi_14_hari(self):
        self.login(ingat_saya=True)
        session = self.client.session
        self.assertFalse(session.get_expire_at_browser_close())
        self.assertEqual(session.get_expiry_age(), 14 * 24 * 60 * 60)

    def test_tanpa_ingat_saya_sesi_berakhir_saat_browser_ditutup(self):
        self.login(ingat_saya=False)
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_login_menolak_permintaan_tanpa_token_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        payload = {"identifier": "TEST-MHS-001", "password": PASSWORD, "tipe": "mahasiswa"}
        self.assertEqual(client.post(LOGIN_URL, payload, format="json").status_code, 403)
        token = client.get(CSRF_URL).json()["csrfToken"]
        response = client.post(LOGIN_URL, payload, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)

    def test_input_tidak_lengkap_ditolak(self):
        response = self.client.post(LOGIN_URL, {"identifier": "TEST-MHS-001"}, format="json")
        self.assertEqual(response.status_code, 400)


class SessionEndpointTests(AuthTestBase):
    def test_me_tanpa_login_ditolak(self):
        self.assertEqual(self.client.get(ME_URL).status_code, 403)

    def test_logout_mengakhiri_sesi(self):
        self.login()
        self.assertEqual(self.client.post(LOGOUT_URL).status_code, 204)
        self.assertEqual(self.client.get(ME_URL).status_code, 403)

    def test_logout_tanpa_login_ditolak(self):
        self.assertEqual(self.client.post(LOGOUT_URL).status_code, 403)


class ChangePasswordTests(AuthTestBase):
    def payload(self, **override):
        data = {
            "password_lama": PASSWORD,
            "password_baru": NEW_PASSWORD,
            "konfirmasi_password": NEW_PASSWORD,
        }
        data.update(override)
        return data

    def test_ganti_password_berhasil(self):
        self.client.force_login(self.mahasiswa)
        response = self.client.post(CHANGE_PASSWORD_URL, self.payload(), format="json")
        self.assertEqual(response.status_code, 200)
        self.mahasiswa.refresh_from_db()
        self.assertTrue(self.mahasiswa.check_password(NEW_PASSWORD))
        self.assertFalse(self.mahasiswa.check_password(PASSWORD))
        # Sesi saat ini tetap berlaku.
        self.assertEqual(self.client.get(ME_URL).status_code, 200)

    def test_ganti_password_menghapus_wajib_ganti(self):
        self.mahasiswa.must_change_password = True
        self.mahasiswa.save()
        self.client.force_login(self.mahasiswa)
        self.client.post(CHANGE_PASSWORD_URL, self.payload(), format="json")
        self.mahasiswa.refresh_from_db()
        self.assertFalse(self.mahasiswa.must_change_password)

    def test_ganti_password_ditolak_untuk_input_tidak_valid(self):
        kasus = {
            "password_lama_salah": self.payload(password_lama="bukan-password-lama"),
            "konfirmasi_berbeda": self.payload(konfirmasi_password="Sandi-Lain-11111?"),
            "sama_dengan_lama": self.payload(
                password_baru=PASSWORD, konfirmasi_password=PASSWORD
            ),
            "terlalu_lemah": self.payload(
                password_baru="12345678", konfirmasi_password="12345678"
            ),
        }
        self.client.force_login(self.mahasiswa)
        for nama, data in kasus.items():
            with self.subTest(kasus=nama):
                response = self.client.post(CHANGE_PASSWORD_URL, data, format="json")
                self.assertEqual(response.status_code, 400)
                self.mahasiswa.refresh_from_db()
                self.assertTrue(self.mahasiswa.check_password(PASSWORD))

    def test_ganti_password_butuh_login(self):
        response = self.client.post(CHANGE_PASSWORD_URL, self.payload(), format="json")
        self.assertEqual(response.status_code, 403)


class UserManagerTests(TestCase):
    def test_create_superuser_berperan_admin(self):
        user = User.objects.create_superuser(
            "TEST-SUPER-001", PASSWORD, nama_lengkap="Superuser Uji Palsu"
        )
        self.assertEqual(user.role, Role.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertFalse(user.must_change_password)

    def test_create_user_tanpa_role_ditolak(self):
        with self.assertRaises(ValueError):
            User.objects.create_user("TEST-X-001", PASSWORD, nama_lengkap="Tanpa Role")

    def test_dua_akun_tanpa_email_tidak_bentrok(self):
        User.objects.create_user("TEST-A-001", PASSWORD, role=Role.DOSEN, nama_lengkap="A Uji")
        User.objects.create_user("TEST-A-002", PASSWORD, role=Role.DOSEN, nama_lengkap="B Uji")
        self.assertEqual(User.objects.filter(email_akademik__isnull=True).count(), 2)


class HasherTests(TestCase):
    def test_password_disimpan_dengan_argon2(self):
        user = User.objects.create_user(
            "TEST-H-001", PASSWORD, role=Role.MAHASISWA, nama_lengkap="Hash Uji"
        )
        self.assertTrue(user.password.startswith("argon2$"))


class PermissionClassTests(SimpleTestCase):
    def request_for(self, user):
        return SimpleNamespace(user=user)

    def make_user(self, role, **kwargs):
        return User(identifier="TEST-P-001", role=role, nama_lengkap="Uji", **kwargs)

    def test_role_sesuai_diizinkan_dan_lainnya_ditolak(self):
        kelas_per_role = {
            Role.MAHASISWA: IsMahasiswa,
            Role.DOSEN: IsDosen,
            Role.ADMIN: IsAdminProdi,
        }
        for role, kelas in kelas_per_role.items():
            for role_lain in Role.values:
                with self.subTest(izin=kelas.__name__, role=role_lain):
                    user = self.make_user(role_lain)
                    diizinkan = kelas().has_permission(self.request_for(user), None)
                    self.assertEqual(diizinkan, role_lain == role)

    def test_anonim_dan_nonaktif_ditolak(self):
        self.assertFalse(IsMahasiswa().has_permission(self.request_for(AnonymousUser()), None))
        nonaktif = self.make_user(Role.MAHASISWA, is_active=False)
        self.assertFalse(IsMahasiswa().has_permission(self.request_for(nonaktif), None))

    def test_wajib_ganti_password_ditolak(self):
        user = self.make_user(Role.DOSEN, must_change_password=True)
        izin = IsDosen()
        self.assertFalse(izin.has_permission(self.request_for(user), None))
        self.assertIn("mengganti password", izin.message)