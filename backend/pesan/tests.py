import io
import os
import shutil
import tempfile
import zipfile
from datetime import date

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Role, User
from akademik.models import Penugasan, PeriodeAkademik, TugasAkhir
from notifikasi.models import Notifikasi

from .models import Percakapan, Pesan
from .services import daftar_percakapan
from .validators import LampiranPesanError, validasi_lampiran

MEDIA_UJI = tempfile.mkdtemp(prefix="simonta-pesan-test-")
PASSWORD = "Password-Uji-2026!"
LIST_URL = "/api/v1/pesan/"


def buat_gambar(format_gambar="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", (3, 3), (20, 90, 50)).save(buffer, format=format_gambar)
    return buffer.getvalue()


def buat_docx():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as arsip:
        arsip.writestr("[Content_Types].xml", "<Types/>")
        arsip.writestr("word/document.xml", "<document/>")
    return buffer.getvalue()


@override_settings(
    MEDIA_ROOT=MEDIA_UJI,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class PesanBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_UJI, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()

        def user(identifier, role, nama):
            return User.objects.create_user(
                identifier, PASSWORD, role=role, nama_lengkap=nama
            )

        self.mhs = user("CHAT-MHS-001", Role.MAHASISWA, "Mahasiswa Chat Uji")
        self.mhs_lain = user("CHAT-MHS-002", Role.MAHASISWA, "Mahasiswa Lain Uji")
        self.dosen = user("CHAT-DSN-001", Role.DOSEN, "Dosen Pembimbing Uji")
        self.pendamping = user("CHAT-DSN-002", Role.DOSEN, "Dosen Pendamping Uji")
        self.asing = user("CHAT-DSN-003", Role.DOSEN, "Dosen Tidak Ditugaskan Uji")
        self.periode = PeriodeAkademik(
            label="Periode Chat Uji",
            tanggal_mulai=date(2030, 1, 1),
            tanggal_selesai=date(2030, 12, 31),
        )
        self.periode.save()
        self.ta = TugasAkhir.objects.create(
            mahasiswa=self.mhs, periode=self.periode, judul="Judul TA Chat Uji"
        )
        Penugasan.objects.create(
            tugas_akhir=self.ta, dosen=self.dosen, peran=Penugasan.Peran.UTAMA
        )
        Penugasan.objects.create(
            tugas_akhir=self.ta, dosen=self.pendamping, peran=Penugasan.Peran.PENDAMPING
        )
        self.ta_lain = TugasAkhir.objects.create(
            mahasiswa=self.mhs_lain, periode=self.periode, judul="TA Mahasiswa Lain"
        )
        Penugasan.objects.create(
            tugas_akhir=self.ta_lain, dosen=self.asing, peran=Penugasan.Peran.UTAMA
        )

    def login(self, user):
        self.client.force_login(user)

    def percakapan(self, dosen=None):
        return Percakapan.objects.get_or_create(
            tugas_akhir=self.ta, dosen=dosen or self.dosen
        )[0]

    def kirim(self, percakapan, **payload):
        self.login(self.mhs)
        return self.client.post(
            f"{LIST_URL}{percakapan.pk}/kirim/", payload, format="multipart"
        )


class PercakapanApiTests(PesanBase):
    def test_daftar_kontak_dibuat_dari_penugasan_dan_tidak_ganda(self):
        self.login(self.mhs)
        pertama = self.client.get(LIST_URL)
        kedua = self.client.get(LIST_URL)
        self.assertEqual(pertama.status_code, 200)
        self.assertEqual(len(pertama.json()), 2)
        self.assertEqual(len(kedua.json()), 2)
        self.assertEqual(Percakapan.objects.filter(tugas_akhir=self.ta).count(), 2)
        self.assertEqual(
            {item["lawan_bicara"]["id"] for item in pertama.json()},
            {self.dosen.pk, self.pendamping.pk},
        )

    def test_dosen_melihat_mahasiswa_yang_ditugaskan_saja(self):
        self.login(self.dosen)
        hasil = self.client.get(LIST_URL).json()
        self.assertEqual(len(hasil), 1)
        self.assertEqual(hasil[0]["lawan_bicara"]["id"], self.mhs.pk)

    def test_pihak_ketiga_tidak_dapat_membaca_thread(self):
        percakapan = self.percakapan()
        self.login(self.asing)
        response = self.client.get(f"{LIST_URL}{percakapan.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_akses_dicabut_jika_penugasan_dihapus(self):
        percakapan = self.percakapan()
        Penugasan.objects.filter(tugas_akhir=self.ta, dosen=self.dosen).delete()
        self.login(self.mhs)
        self.assertEqual(self.client.get(f"{LIST_URL}{percakapan.pk}/").status_code, 404)
        self.login(self.dosen)
        self.assertEqual(self.client.get(f"{LIST_URL}{percakapan.pk}/").status_code, 404)

    def test_pesan_tanpa_peserta_ditolak(self):
        percakapan = self.percakapan()
        self.login(self.asing)
        response = self.client.post(
            f"{LIST_URL}{percakapan.pk}/kirim/", {"isi": "Tidak berhak"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Pesan.objects.count(), 0)

    def test_butuh_login_dan_role_mahasiswa_atau_dosen(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 403)
        percakapan = self.percakapan()
        self.login(self.mhs_lain)
        self.assertEqual(self.client.get(f"{LIST_URL}{percakapan.pk}/").status_code, 404)


class PesanApiTests(PesanBase):
    def test_kirim_pesan_notifikasi_dan_pratinjau_daftar(self):
        percakapan = self.percakapan()
        response = self.kirim(percakapan, isi="  Halo pembimbing.  ")
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["isi"], "Halo pembimbing.")
        self.assertTrue(body["saya_pengirim"])
        self.assertEqual(
            Notifikasi.objects.filter(user=self.dosen, jenis=Notifikasi.Jenis.PESAN_BARU).count(),
            1,
        )
        self.login(self.dosen)
        rows = self.client.get(LIST_URL).json()
        row = next(item for item in rows if item["lawan_bicara"]["id"] == self.mhs.pk)
        self.assertEqual(row["pesan_terakhir"]["isi"], "Halo pembimbing.")
        self.assertEqual(row["jumlah_belum_dibaca"], 1)

    def test_after_hanya_mengembalikan_pesan_baru(self):
        percakapan = self.percakapan()
        pertama = self.kirim(percakapan, isi="Pesan pertama").json()
        self.kirim(percakapan, isi="Pesan kedua")
        self.login(self.dosen)
        response = self.client.get(f"{LIST_URL}{percakapan.pk}/?after={pertama['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["isi"] for item in response.json()["pesan"]], ["Pesan kedua"])

    def test_after_tidak_valid(self):
        percakapan = self.percakapan()
        self.login(self.mhs)
        self.assertEqual(self.client.get(f"{LIST_URL}{percakapan.pk}/?after=abc").status_code, 400)

    def test_tandai_dibaca_mengubah_status_pesan(self):
        percakapan = self.percakapan()
        self.kirim(percakapan, isi="Periksa bab dua, Pak.")
        pesan = Pesan.objects.get(percakapan=percakapan)
        self.assertIsNone(pesan.dibaca_pada)
        self.login(self.dosen)
        response = self.client.post(f"{LIST_URL}{percakapan.pk}/dibaca/")
        self.assertEqual(response.status_code, 200)
        pesan.refresh_from_db()
        self.assertIsNotNone(pesan.dibaca_pada)
        self.assertEqual(response.json()["ditandai"], 1)
        self.login(self.mhs)
        self.assertIsNotNone(self.client.get(f"{LIST_URL}{percakapan.pk}/").json()["pesan"][0]["dibaca_pada"])

    def test_hanya_pesan_masuk_yang_ditandai_dibaca(self):
        percakapan = self.percakapan()
        self.kirim(percakapan, isi="Pesan dari mahasiswa")
        self.login(self.dosen)
        self.client.post(f"{LIST_URL}{percakapan.pk}/dibaca/")
        self.client.post(f"{LIST_URL}{percakapan.pk}/kirim/", {"isi": "Balasan dosen"})
        self.login(self.dosen)
        self.client.post(f"{LIST_URL}{percakapan.pk}/dibaca/")
        pesan = list(Pesan.objects.filter(percakapan=percakapan).order_by("id"))
        self.assertIsNotNone(pesan[0].dibaca_pada)
        self.assertIsNone(pesan[1].dibaca_pada)

    def test_pesan_kosong_ditolak(self):
        percakapan = self.percakapan()
        response = self.kirim(percakapan, isi="")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Pesan.objects.count(), 0)


class LampiranValidationTests(PesanBase):
    def test_pdf_dan_docx_valid(self):
        # Validator menolak PDF palsu; PDF sah diuji dengan PDF minimal yang dibuat pypdf.
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        buffer = io.BytesIO()
        writer.write(buffer)
        pdf = SimpleUploadedFile("materi.pdf", buffer.getvalue())
        self.assertEqual(validasi_lampiran(pdf).ekstensi, ".pdf")
        docx = SimpleUploadedFile("materi.docx", buat_docx())
        self.assertEqual(validasi_lampiran(docx).ekstensi, ".docx")

    def test_jpg_png_valid(self):
        jpg = SimpleUploadedFile("foto.jpg", buat_gambar("JPEG"))
        png = SimpleUploadedFile("gambar.png", buat_gambar("PNG"))
        self.assertEqual(validasi_lampiran(jpg).ekstensi, ".jpg")
        self.assertEqual(validasi_lampiran(png).ekstensi, ".png")

    def test_ekstensi_isi_palsu_dan_ukuran_ditolak(self):
        with self.assertRaises(LampiranPesanError):
            validasi_lampiran(SimpleUploadedFile("program.exe", b"MZ"))
        with self.assertRaises(LampiranPesanError):
            validasi_lampiran(SimpleUploadedFile("palsu.pdf", b"hanya teks"))
        with self.assertRaises(LampiranPesanError):
            validasi_lampiran(SimpleUploadedFile("besar.png", b"x" * (15 * 1024 * 1024 + 1)))

    def test_kirim_lampiran_dan_unduh_hanya_peserta(self):
        percakapan = self.percakapan()
        response = self.kirim(
            percakapan,
            isi="File pendukung",
            lampiran=SimpleUploadedFile("gambar.png", buat_gambar("PNG")),
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["nama_lampiran"], "gambar.png")
        self.assertIn("/api/v1/pesan/lampiran/", body["lampiran_url"])
        self.login(self.asing)
        self.assertEqual(self.client.get(body["lampiran_url"]).status_code, 404)
        self.login(self.dosen)
        thread = self.client.get(f"{LIST_URL}{percakapan.pk}/").json()
        url_dosen = thread["pesan"][0]["lampiran_url"]
        self.assertEqual(self.client.get(url_dosen).status_code, 200)
