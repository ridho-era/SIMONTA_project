import io
import re
import shutil
import tempfile
import zipfile
from datetime import date
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from pypdf import PdfWriter
from rest_framework.test import APIClient

from accounts.models import Role, User
from akademik.models import MilestoneTemplate, Penugasan, PeriodeAkademik, TugasAkhir
from milestone.services import buat_milestone_untuk_ta, verifikasi
from notifikasi.models import Notifikasi

from .models import Dokumen, DokumenVersi
from .services import buat_token_unduh, url_pratinjau, url_unduh
from .validators import MAKS_UKURAN, BerkasError, bersihkan_nama, validasi_berkas

PASSWORD = "Sandi-Uji-12345!"  # semua data sintetis dan jelas palsu
URL = "/api/v1/mahasiswa/dokumen/"
MEDIA_UJI = tempfile.mkdtemp(prefix="simonta-uji-")


def tearDownModule():
    shutil.rmtree(MEDIA_UJI, ignore_errors=True)


def buat_pdf(halaman=1):
    penulis = PdfWriter()
    for _ in range(halaman):
        penulis.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    penulis.write(buf)
    return buf.getvalue()


def buat_docx(tambahan=()):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as arsip:
        arsip.writestr("[Content_Types].xml", "<Types/>")
        arsip.writestr("word/document.xml", "<document/>")
        for nama in tambahan:
            arsip.writestr(nama, "x")
    return buf.getvalue()


def berkas(nama, isi):
    return SimpleUploadedFile(nama, isi)


class ValidasiBerkasTests(SimpleTestCase):
    def galat(self, nama, isi):
        with self.assertRaises(BerkasError) as ctx:
            validasi_berkas(berkas(nama, isi))
        return str(ctx.exception)

    def test_pdf_valid_menghitung_halaman(self):
        hasil = validasi_berkas(berkas("draf-uji.pdf", buat_pdf(3)))
        self.assertEqual((hasil.halaman, hasil.ekstensi, hasil.nama_asli), (3, ".pdf", "draf-uji.pdf"))

    def test_docx_valid_tanpa_halaman(self):
        hasil = validasi_berkas(berkas("draf-uji.DOCX", buat_docx()))
        self.assertEqual((hasil.halaman, hasil.ekstensi), (None, ".docx"))

    def test_ekstensi_lain_ditolak(self):
        self.assertIn("PDF atau DOCX", self.galat("draf-uji.exe", b"MZ"))
        self.assertIn("PDF atau DOCX", self.galat("draf-uji.txt", b"teks"))
        self.assertIn("PDF atau DOCX", self.galat("tanpa-ekstensi", buat_pdf()))

    def test_isi_tidak_sesuai_ekstensi_ditolak(self):
        self.assertIn("bukan PDF", self.galat("draf-uji.pdf", b"ini hanya teks biasa"))
        self.assertIn("bukan DOCX", self.galat("draf-uji.docx", b"ini hanya teks biasa"))
        self.assertIn("bukan DOCX", self.galat("draf-uji.docx", buat_pdf()))
        self.assertIn("bukan PDF", self.galat("draf-uji.pdf", buat_docx()))

    def test_pdf_rusak_dan_terkunci_ditolak(self):
        self.assertIn("rusak", self.galat("draf-uji.pdf", b"%PDF-1.4 sampah"))
        penulis = PdfWriter()
        penulis.add_blank_page(width=72, height=72)
        penulis.encrypt("rahasia-uji")
        buf = io.BytesIO()
        penulis.write(buf)
        self.assertIn("password", self.galat("draf-uji.pdf", buf.getvalue()))

    def test_docx_tanpa_struktur_word_atau_bermakro_ditolak(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as arsip:
            arsip.writestr("berkas.txt", "x")
        self.assertIn("bukan DOCX", self.galat("draf-uji.docx", buf.getvalue()))
        self.assertIn("makro", self.galat("draf-uji.docx", buat_docx(["word/vbaProject.bin"])))

    def test_berkas_kosong_dan_terlalu_besar_ditolak(self):
        self.assertIn("kosong", self.galat("draf-uji.pdf", b""))
        self.assertIn("15 MB", self.galat("draf-uji.pdf", b"%PDF-" + b"0" * MAKS_UKURAN))

    def test_nama_dibersihkan(self):
        self.assertEqual(bersihkan_nama("../../rahasia.pdf"), "rahasia.pdf")
        self.assertEqual(bersihkan_nama("C:\\folder\\laporan akhir.pdf"), "laporan akhir.pdf")
        self.assertEqual(bersihkan_nama("a\x00b.pdf"), "ab.pdf")
        self.assertEqual(len(bersihkan_nama("a" * 400 + ".pdf")), 255)


@override_settings(
    MEDIA_ROOT=MEDIA_UJI,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class Dasar(TestCase):
    def setUp(self):
        self.client = APIClient()

        def user(identifier, role, nama):
            return User.objects.create_user(identifier, PASSWORD, role=role, nama_lengkap=nama)

        self.mhs = user("TEST-MHS-001", Role.MAHASISWA, "Mahasiswa Uji Palsu")
        self.mhs2 = user("TEST-MHS-002", Role.MAHASISWA, "Mahasiswa Uji Palsu Dua")
        self.utama = user("TEST-DSN-001", Role.DOSEN, "Dosen Utama Uji Palsu")
        self.pendamping = user("TEST-DSN-002", Role.DOSEN, "Dosen Pendamping Uji Palsu")
        self.penguji = user("TEST-DSN-003", Role.DOSEN, "Dosen Penguji Uji Palsu")
        self.asing = user("TEST-DSN-009", Role.DOSEN, "Dosen Asing Uji Palsu")
        self.periode = PeriodeAkademik(label="Periode Uji", tanggal_mulai=date(2030, 1, 1), tanggal_selesai=date(2030, 6, 30))
        self.periode.save()
        for urutan, bobot in enumerate(["30", "30", "40"], start=1):
            MilestoneTemplate.objects.create(urutan=urutan, nama=f"Tahap Uji {urutan}", bobot=Decimal(bobot))
        self.ta = TugasAkhir.objects.create(mahasiswa=self.mhs, periode=self.periode, judul="Judul Uji Palsu")
        for dosen, peran in [(self.utama, "utama"), (self.pendamping, "pendamping"), (self.penguji, "penguji")]:
            Penugasan.objects.create(tugas_akhir=self.ta, dosen=dosen, peran=peran)
        buat_milestone_untuk_ta(self.ta)
        self.ms = list(self.ta.milestone.order_by("urutan"))

    def unggah(self, milestone_id, isi=None, nama="draf-uji.pdf", catatan=""):
        return self.client.post(
            URL,
            {"milestone": milestone_id, "berkas": SimpleUploadedFile(nama, buat_pdf() if isi is None else isi), "catatan": catatan},
            format="multipart",
        )


class UnggahApiTests(Dasar):
    def test_butuh_login_dan_peran_mahasiswa(self):
        self.assertEqual(self.unggah(self.ms[0].pk).status_code, 403)
        self.client.force_login(self.utama)
        self.assertEqual(self.unggah(self.ms[0].pk).status_code, 403)

    def test_unggah_pdf_berhasil(self):
        self.client.force_login(self.mhs)
        isi = buat_pdf(2)
        r = self.unggah(self.ms[0].pk, isi, catatan="  Catatan uji  ")
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual((body["nomor_versi"], body["halaman"], body["ukuran"]), (1, 2, len(isi)))
        self.assertEqual((body["status"], body["nama_asli"], body["catatan"]), ("menunggu_review", "draf-uji.pdf", "Catatan uji"))
        self.assertEqual(body["milestone"]["id"], self.ms[0].pk)
        versi = DokumenVersi.objects.get(pk=body["id"])
        self.assertRegex(versi.berkas.name, r"^dokumen/[0-9a-f]{32}\.pdf$")

    def test_nama_berkas_aman(self):
        self.client.force_login(self.mhs)
        versi = DokumenVersi.objects.get(pk=self.unggah(self.ms[0].pk, nama="../../rahasia.pdf").json()["id"])
        self.assertEqual(versi.nama_asli, "rahasia.pdf")
        self.assertNotIn("rahasia", versi.berkas.name)

    def test_docx_diterima_tanpa_halaman(self):
        self.client.force_login(self.mhs)
        r = self.unggah(self.ms[0].pk, buat_docx(), nama="draf-uji.docx")
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.json()["halaman"])

    def test_versi_bertambah_dan_versi_lama_utuh(self):
        self.client.force_login(self.mhs)
        isi = [buat_pdf(1), buat_pdf(2), buat_pdf(3)]
        for i in isi:
            self.assertEqual(self.unggah(self.ms[0].pk, i).status_code, 201)
        self.assertEqual(Dokumen.objects.count(), 1)
        versi = list(DokumenVersi.objects.order_by("nomor_versi"))
        self.assertEqual([v.nomor_versi for v in versi], [1, 2, 3])
        self.assertEqual(len({v.berkas.name for v in versi}), 3)
        for v, asli in zip(versi, isi):
            with v.berkas.open("rb") as f:
                self.assertEqual(f.read(), asli)

    def test_ekstensi_dan_isi_palsu_ditolak(self):
        self.client.force_login(self.mhs)
        self.assertEqual(self.unggah(self.ms[0].pk, b"MZ", nama="draf-uji.exe").status_code, 400)
        r = self.unggah(self.ms[0].pk, b"hanya teks", nama="draf-uji.pdf")
        self.assertEqual(r.status_code, 400)
        self.assertIn("berkas", r.json())
        self.assertEqual(DokumenVersi.objects.count(), 0)
        self.assertEqual(Notifikasi.objects.count(), 0)

    def test_ukuran_melebihi_batas_ditolak(self):
        self.client.force_login(self.mhs)
        r = self.unggah(self.ms[0].pk, b"%PDF-" + b"0" * MAKS_UKURAN)
        self.assertEqual(r.status_code, 400)
        self.assertIn("15 MB", r.json()["berkas"][0])
        self.assertEqual(DokumenVersi.objects.count(), 0)

    def test_field_wajib(self):
        self.client.force_login(self.mhs)
        self.assertEqual(self.client.post(URL, {"milestone": self.ms[0].pk}, format="multipart").status_code, 400)
        self.assertEqual(self.client.post(URL, {}, format="multipart").status_code, 400)

    def test_milestone_terkunci_ditolak(self):
        self.client.force_login(self.mhs)
        r = self.unggah(self.ms[1].pk)
        self.assertEqual(r.status_code, 409)
        self.assertIn("terkunci", r.json()["detail"])
        self.assertEqual(Dokumen.objects.count(), 0)
        self.assertEqual(Notifikasi.objects.count(), 0)

    def test_milestone_terverifikasi_ditolak_dan_tahap_berikutnya_terbuka(self):
        verifikasi(self.ms[0], 100, self.utama)
        self.client.force_login(self.mhs)
        self.assertEqual(self.unggah(self.ms[0].pk).status_code, 409)
        self.assertEqual(self.unggah(self.ms[1].pk).status_code, 201)

    def test_ta_tidak_aktif_ditolak(self):
        TugasAkhir.objects.filter(pk=self.ta.pk).update(status="selesai", slot_aktif=None)
        self.client.force_login(self.mhs)
        self.assertEqual(self.unggah(self.ms[0].pk).status_code, 409)

    def test_milestone_milik_orang_lain_404(self):
        ta2 = TugasAkhir.objects.create(mahasiswa=self.mhs2, periode=self.periode, judul="Judul Uji Dua")
        buat_milestone_untuk_ta(ta2)
        self.client.force_login(self.mhs2)
        self.assertEqual(self.unggah(self.ms[0].pk).status_code, 404)
        self.assertEqual(self.unggah(999999).status_code, 404)
        self.assertEqual(DokumenVersi.objects.count(), 0)

    def test_mahasiswa_tanpa_ta_409(self):
        self.client.force_login(self.mhs2)
        self.assertEqual(self.unggah(self.ms[0].pk).status_code, 409)

    def test_notifikasi_ke_pembimbing_utama_dan_pendamping(self):
        self.client.force_login(self.mhs)
        self.unggah(self.ms[0].pk)
        notif = Notifikasi.objects.filter(jenis="dokumen_baru")
        self.assertEqual({n.user for n in notif}, {self.utama, self.pendamping})
        self.assertTrue(all(n.dibaca_pada is None and "versi 1" in n.isi for n in notif))


class RiwayatApiTests(Dasar):
    def test_butuh_peran_mahasiswa(self):
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.client.force_login(self.utama)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_empty_state_dan_pilihan_milestone(self):
        self.client.force_login(self.mhs)
        body = self.client.get(URL).json()
        self.assertEqual(body["tugas_akhir"]["id"], self.ta.pk)
        self.assertEqual((body["riwayat"]["jumlah"], body["riwayat"]["hasil"]), (0, []))
        self.assertEqual([m["dapat_unggah"] for m in body["milestone"]], [True, False, False])
        self.assertEqual([m["alasan"] for m in body["milestone"]], ["", "Terkunci", "Terkunci"])
        self.assertEqual(body["batas"], {"ukuran_maks_mb": 15, "ekstensi": [".pdf", ".docx"]})

    def test_pilihan_setelah_verifikasi(self):
        verifikasi(self.ms[0], 100, self.utama)
        self.client.force_login(self.mhs)
        body = self.client.get(URL).json()
        self.assertEqual([m["dapat_unggah"] for m in body["milestone"]], [False, True, False])
        self.assertEqual(body["milestone"][0]["alasan"], "Sudah diverifikasi")

    def test_mahasiswa_tanpa_ta(self):
        self.client.force_login(self.mhs2)
        body = self.client.get(URL).json()
        self.assertIsNone(body["tugas_akhir"])
        self.assertEqual((body["milestone"], body["riwayat"]["hasil"]), ([], []))

    def test_riwayat_terbaru_dahulu_dan_filter_milestone(self):
        self.client.force_login(self.mhs)
        self.unggah(self.ms[0].pk)
        self.unggah(self.ms[0].pk)
        verifikasi(self.ms[0], 100, self.utama)
        self.unggah(self.ms[1].pk)
        semua = self.client.get(URL).json()["riwayat"]
        self.assertEqual(semua["jumlah"], 3)
        self.assertEqual(semua["hasil"][0]["milestone"]["id"], self.ms[1].pk)
        self.assertTrue(all(h["unduh_url"].startswith("/api/v1/berkas/") for h in semua["hasil"]))
        self.assertTrue(all(h["pratinjau_url"].startswith("/api/v1/berkas/") for h in semua["hasil"]))
        saring = self.client.get(URL, {"milestone": self.ms[0].pk}).json()["riwayat"]
        self.assertEqual([h["nomor_versi"] for h in saring["hasil"]], [2, 1])

    def test_paginasi_20_baris(self):
        dokumen = Dokumen.objects.create(milestone=self.ms[0])
        for i in range(1, 26):
            DokumenVersi.objects.create(
                dokumen=dokumen, nomor_versi=i, berkas=f"dokumen/palsu{i}.pdf", nama_asli=f"palsu{i}.pdf", ukuran=1
            )
        self.client.force_login(self.mhs)
        r1 = self.client.get(URL).json()["riwayat"]
        self.assertEqual((len(r1["hasil"]), r1["jumlah"], r1["halaman"], r1["total_halaman"]), (20, 25, 1, 2))
        self.assertEqual(len(self.client.get(URL, {"halaman": 2}).json()["riwayat"]["hasil"]), 5)
        self.assertEqual(self.client.get(URL, {"halaman": "abc"}).json()["riwayat"]["halaman"], 1)
        self.assertEqual(self.client.get(URL, {"halaman": 99}).json()["riwayat"]["halaman"], 2)

    def test_data_mahasiswa_lain_tidak_bocor(self):
        ta2 = TugasAkhir.objects.create(mahasiswa=self.mhs2, periode=self.periode, judul="Judul Uji Dua")
        buat_milestone_untuk_ta(ta2)
        self.client.force_login(self.mhs2)
        self.assertEqual(self.unggah(ta2.milestone.order_by("urutan").first().pk).status_code, 201)
        self.client.force_login(self.mhs)
        self.assertEqual(self.client.get(URL).json()["riwayat"]["jumlah"], 0)


class UnduhApiTests(Dasar):
    def setUp(self):
        super().setUp()
        self.isi = buat_pdf(2)
        self.client.force_login(self.mhs)
        r = self.unggah(self.ms[0].pk, self.isi, nama="laporan uji.pdf")
        self.versi = DokumenVersi.objects.get(pk=r.json()["id"])
        self.url = r.json()["unduh_url"]
        self.client.logout()

    def unduh(self, user, url=None):
        self.client.logout()
        if user is not None:
            self.client.force_login(user)
        return self.client.get(url or url_unduh(user, self.versi))

    def test_pemilik_dapat_mengunduh_sebagai_lampiran(self):
        self.client.force_login(self.mhs)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), self.isi)
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertIn("laporan uji.pdf", r["Content-Disposition"])
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_pemilik_dapat_membuka_pratinjau_inline(self):
        url = url_pratinjau(self.mhs, self.versi)
        response = self.unduh(self.mhs, url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), self.isi)
        self.assertIn("inline", response["Content-Disposition"])
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_pratinjau_docx_disajikan_dengan_mime_type_docx(self):
        versi_docx = DokumenVersi(
            dokumen=self.versi.dokumen,
            nomor_versi=2,
            nama_asli="dokumen-uji.docx",
            ukuran=len(buat_docx()),
        )
        versi_docx.berkas.save("dokumen-uji.docx", ContentFile(buat_docx()), save=True)
        response = self.unduh(self.mhs, url_pratinjau(self.mhs, versi_docx))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertIn("inline", response["Content-Disposition"])

    def test_pembimbing_utama_dan_pendamping_dapat_membuka_pratinjau(self):
        for dosen in (self.utama, self.pendamping):
            with self.subTest(dosen=dosen.identifier):
                url = url_pratinjau(dosen, self.versi)
                response = self.unduh(dosen, url)
                self.assertEqual(response.status_code, 200)
                self.assertIn("inline", response["Content-Disposition"])

    def test_pratinjau_tidak_dapat_diakses_orang_lain_atau_tanpa_token(self):
        self.assertEqual(self.unduh(self.asing, url_pratinjau(self.asing, self.versi)).status_code, 404)
        self.assertEqual(self.unduh(self.mhs2, url_pratinjau(self.mhs, self.versi)).status_code, 404)
        base = f"/api/v1/berkas/{self.versi.pk}/pratinjau/"
        self.assertEqual(self.unduh(self.mhs, base).status_code, 403)
        self.assertEqual(self.unduh(self.mhs, base + "?token=tidak-valid").status_code, 403)

    def test_dosen_yang_ditugaskan_dapat_mengunduh(self):
        for dosen in (self.utama, self.pendamping, self.penguji):
            with self.subTest(dosen=dosen.identifier):
                self.assertEqual(self.unduh(dosen).status_code, 200)

    def test_pengguna_tidak_berhak_mendapat_404(self):
        self.assertEqual(self.unduh(self.asing).status_code, 404)
        self.assertEqual(self.unduh(self.mhs2, url_unduh(self.mhs, self.versi)).status_code, 404)

    def test_anonim_ditolak(self):
        self.assertEqual(self.unduh(None, self.url).status_code, 403)

    def test_wajib_ganti_password_diblokir(self):
        User.objects.filter(pk=self.mhs.pk).update(must_change_password=True)
        self.assertEqual(self.unduh(self.mhs, self.url).status_code, 403)

    def test_token_wajib_dan_terikat_pengguna_serta_berkas(self):
        base = f"/api/v1/berkas/{self.versi.pk}/unduh/"
        self.assertEqual(self.unduh(self.mhs, base).status_code, 403)
        self.assertEqual(self.unduh(self.mhs, base + "?token=ngawur").status_code, 403)
        token_orang_lain = buat_token_unduh(self.utama, self.versi)
        self.assertEqual(self.unduh(self.mhs, f"{base}?token={token_orang_lain}").status_code, 403)
        versi2 = DokumenVersi.objects.create(
            dokumen=self.versi.dokumen, nomor_versi=2, berkas="dokumen/palsu.pdf", nama_asli="palsu.pdf", ukuran=1
        )
        token_versi_lain = buat_token_unduh(self.mhs, versi2)
        self.assertEqual(self.unduh(self.mhs, f"{base}?token={token_versi_lain}").status_code, 403)

    @override_settings(UNDUH_TOKEN_MAX_AGE=-1)
    def test_token_kedaluwarsa(self):
        self.assertEqual(self.unduh(self.mhs, self.url).status_code, 410)

    def test_berkas_hilang_404(self):
        default_storage.delete(self.versi.berkas.name)
        self.assertEqual(self.unduh(self.mhs, self.url).status_code, 404)

    def test_berkas_tidak_disajikan_sebagai_url_publik(self):
        self.assertEqual(self.client.get("/media/" + self.versi.berkas.name).status_code, 404)


class VersiTidakDapatDiubahTests(Dasar):
    def test_hanya_status_yang_boleh_berubah(self):
        dokumen = Dokumen.objects.create(milestone=self.ms[0])
        versi = DokumenVersi(dokumen=dokumen, nomor_versi=1, nama_asli="asli.pdf", ukuran=1)
        versi.berkas.save("asli.pdf", ContentFile(buat_pdf()), save=False)
        versi.save()
        versi.nama_asli = "diganti.pdf"
        with self.assertRaises(ValueError):
            versi.save()
        with self.assertRaises(ValueError):
            versi.save(update_fields=["nama_asli"])
        versi.status = DokumenVersi.Status.PERLU_REVISI
        versi.save(update_fields=["status"])
        versi.refresh_from_db()
        self.assertEqual((versi.status, versi.nama_asli), ("perlu_revisi", "asli.pdf"))