import io
import random
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from akademik.models import Penugasan, PeriodeAkademik, ProgramStudi, TugasAkhir
from audit.models import AuditLog
from .models import Role

User = get_user_model()
PASSWORD = "Sandi-Uji-Profil-123!"
PROFILE_URL = "/api/v1/profil/"
PHOTO_URL = "/api/v1/profil/foto/"
SESSIONS_URL = "/api/v1/profil/sesi/keluar-perangkat-lain/"

FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


def gambar_valid(format_gambar="JPEG", ukuran=(24, 24)):
    buffer = io.BytesIO()
    Image.new("RGB", ukuran, (40, 100, 80)).save(buffer, format=format_gambar)
    ekstensi = "jpg" if format_gambar == "JPEG" else "png"
    return SimpleUploadedFile(
        f"foto.{ekstensi}", buffer.getvalue(),
        content_type="image/jpeg" if format_gambar == "JPEG" else "image/png",
    )


def gambar_besar_jpg():
    ukuran = (1500, 1500)
    sumber = random.Random(42).randbytes(ukuran[0] * ukuran[1] * 3)
    gambar = Image.frombytes("RGB", ukuran, sumber)
    buffer = io.BytesIO()
    gambar.save(buffer, format="JPEG", quality=100, subsampling=0)
    return SimpleUploadedFile("foto-besar.jpg", buffer.getvalue(), content_type="image/jpeg")


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class ProfilApiTests(TestCase):
    def setUp(self):
        self.program = ProgramStudi.objects.create(nama="Program Studi Uji Integrasi")
        self.mahasiswa = User.objects.create_user(
            "TEST-PROFIL-MHS", PASSWORD, role=Role.MAHASISWA,
            nama_lengkap="Mahasiswa Uji Profil", email_akademik="mahasiswa-profil@example.invalid",
            telepon="080000000001", program_studi=self.program,
        )
        self.dosen = User.objects.create_user(
            "TEST-PROFIL-DSN", PASSWORD, role=Role.DOSEN,
            nama_lengkap="Dosen Uji Profil", email_akademik="dosen-profil@example.invalid",
            telepon="080000000002", program_studi=self.program,
        )
        self.admin = User.objects.create_user(
            "TEST-PROFIL-ADM", PASSWORD, role=Role.ADMIN,
            nama_lengkap="Admin Uji Profil",
        )
        self.client = APIClient()

    def test_mahasiswa_mendapat_data_pribadi_dan_program_studi_read_only(self):
        self.client.force_login(self.mahasiswa)
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["identifier"], "TEST-PROFIL-MHS")
        self.assertEqual(body["program_studi"], {"id": self.program.pk, "nama": self.program.nama})
        self.assertIsNone(body["konteks_akademik"]["tugas_akhir"])

    def test_field_read_only_ditolak_dan_database_tidak_berubah(self):
        self.client.force_login(self.mahasiswa)
        response = self.client.patch(
            PROFILE_URL,
            {
                "nama_lengkap": "Nama Baru Uji",
                "identifier": "NPM-UBAH-PAKSA",
                "email_akademik": "ubah@example.invalid",
                "program_studi": self.program.pk + 100,
                "judul": "Judul yang tidak boleh diubah",
                "periode": 9999,
                "pembimbing": [],
                "penguji": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.mahasiswa.refresh_from_db()
        self.assertEqual(self.mahasiswa.identifier, "TEST-PROFIL-MHS")
        self.assertEqual(self.mahasiswa.email_akademik, "mahasiswa-profil@example.invalid")
        self.assertEqual(self.mahasiswa.nama_lengkap, "Mahasiswa Uji Profil")

    def test_mahasiswa_dapat_mengubah_nama_dan_telepon_dan_diaudit(self):
        self.client.force_login(self.mahasiswa)
        response = self.client.patch(
            PROFILE_URL,
            {"nama_lengkap": "Nama Mahasiswa Diperbarui", "telepon": "081234567890"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.mahasiswa.refresh_from_db()
        self.assertEqual(self.mahasiswa.nama_lengkap, "Nama Mahasiswa Diperbarui")
        self.assertTrue(AuditLog.objects.filter(aktor=self.mahasiswa, aksi=AuditLog.Aksi.UBAH).exists())

    def test_konteks_mahasiswa_menampilkan_ta_periode_pembimbing_dan_penguji(self):
        periode = PeriodeAkademik.objects.create(
            label="Periode Uji Profil", tanggal_mulai="2026-01-01", tanggal_selesai="2026-12-31"
        )
        ta = TugasAkhir.objects.create(
            mahasiswa=self.mahasiswa, periode=periode, judul="Judul TA Uji Profil",
            status=TugasAkhir.Status.AKTIF,
        )
        Penugasan.objects.create(tugas_akhir=ta, dosen=self.dosen, peran=Penugasan.Peran.UTAMA)
        self.client.force_login(self.mahasiswa)
        response = self.client.get(PROFILE_URL)
        konteks = response.json()["konteks_akademik"]
        self.assertEqual(konteks["tugas_akhir"]["judul"], ta.judul)
        self.assertEqual(konteks["periode"]["label"], periode.label)
        self.assertEqual(konteks["pembimbing"][0]["identifier"], self.dosen.identifier)
        self.assertEqual(konteks["penguji"], [])

    def test_ringkasan_dosen_menghitung_mahasiswa_bimbingan_aktif(self):
        periode = PeriodeAkademik.objects.create(
            label="Periode Uji Dosen", tanggal_mulai="2026-01-01", tanggal_selesai="2026-12-31"
        )
        ta = TugasAkhir.objects.create(
            mahasiswa=self.mahasiswa, periode=periode, judul="Judul TA Dosen Uji",
            status=TugasAkhir.Status.AKTIF,
        )
        Penugasan.objects.create(tugas_akhir=ta, dosen=self.dosen, peran=Penugasan.Peran.UTAMA)
        self.client.force_login(self.dosen)
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["konteks_akademik"]["jumlah_mahasiswa_bimbingan"], 1)

    def test_dosen_dapat_mengubah_nama_gelar_dan_telepon(self):
        self.client.force_login(self.dosen)
        response = self.client.patch(
            PROFILE_URL,
            {"nama_lengkap": "Dosen Uji Diperbarui", "gelar": "M.Kom.", "telepon": "081111111111"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.dosen.refresh_from_db()
        self.assertEqual(self.dosen.gelar, "M.Kom.")
        self.assertEqual(self.dosen.telepon, "081111111111")

    def test_mahasiswa_tidak_dapat_mengubah_gelar(self):
        self.client.force_login(self.mahasiswa)
        response = self.client.patch(PROFILE_URL, {"gelar": "M.Kom."}, format="json")
        self.assertEqual(response.status_code, 400)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="simonta-profile-test-"))
    def test_foto_jpg_dan_png_dapat_diunggah(self):
        self.client.force_login(self.mahasiswa)
        response_jpg = self.client.patch(PROFILE_URL, {"foto": gambar_valid("JPEG")}, format="multipart")
        self.assertEqual(response_jpg.status_code, 200)
        self.assertTrue(response_jpg.json()["punya_foto"])
        response_png = self.client.patch(PROFILE_URL, {"foto": gambar_valid("PNG")}, format="multipart")
        self.assertEqual(response_png.status_code, 200)
        self.assertTrue(response_png.json()["punya_foto"])
        foto = self.client.get(PHOTO_URL)
        self.assertEqual(foto.status_code, 200)
        self.assertTrue(foto["Content-Type"].startswith("image/png"))
        self.assertEqual(foto["Cache-Control"], "private, no-store")

    def test_foto_tipe_tidak_didukung_ditolak(self):
        self.client.force_login(self.mahasiswa)
        gif = io.BytesIO()
        Image.new("RGB", (2, 2), (1, 2, 3)).save(gif, format="GIF")
        file_gif = SimpleUploadedFile("foto.gif", gif.getvalue(), content_type="image/gif")
        response = self.client.patch(PROFILE_URL, {"foto": file_gif}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_foto_lebih_dari_dua_mb_ditolak(self):
        self.client.force_login(self.mahasiswa)
        berkas = gambar_besar_jpg()
        self.assertGreater(berkas.size, 2 * 1024 * 1024)
        response = self.client.patch(PROFILE_URL, {"foto": berkas}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("2 MB", str(response.json()))

    def test_foto_tidak_dapat_diakses_tanpa_login(self):
        response = self.client.get(PHOTO_URL)
        self.assertEqual(response.status_code, 403)

    def test_admin_tidak_dapat_mengakses_profil_portal(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(PROFILE_URL).status_code, 403)

    def test_keluar_perangkat_lain_membatalkan_sesi_lain_dan_mempertahankan_saat_ini(self):
        client_lain = APIClient()
        self.client.force_login(self.dosen)
        client_lain.force_login(self.dosen)
        self.assertGreaterEqual(Session.objects.filter(expire_date__gt=timezone.now()).count(), 2)
        response = self.client.post(SESSIONS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["jumlah_sesi_dikeluarkan"], 1)
        self.assertTrue(response.json()["sesi_saat_ini_dipertahankan"])
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 200)
        self.assertEqual(client_lain.get("/api/v1/auth/me/").status_code, 403)
        self.assertTrue(AuditLog.objects.filter(aktor=self.dosen, keterangan__icontains="perangkat lain").exists())

    def test_perubahan_password_dicatat_tanpa_menyimpan_password(self):
        self.client.force_login(self.mahasiswa)
        response = self.client.post(
            "/api/v1/auth/change-password/",
            {
                "password_lama": PASSWORD,
                "password_baru": "Violet-Bridge-9274!",
                "konfirmasi_password": "Violet-Bridge-9274!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        audit = AuditLog.objects.filter(
            aktor=self.mahasiswa, aksi=AuditLog.Aksi.RESET_PASSWORD
        ).latest("id")
        self.assertIn("mengganti password", audit.keterangan)
        self.assertNotIn("password", str(audit.sebelum).lower())
        self.assertNotIn("password", str(audit.sesudah).lower())

    def test_mahasiswa_tidak_dapat_mencabut_sesi_dari_endpoint_dosen(self):
        self.client.force_login(self.mahasiswa)
        self.assertEqual(self.client.post(SESSIONS_URL).status_code, 403)
