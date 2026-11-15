import io
import os
import shutil
import tempfile
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from pypdf import PdfWriter
from rest_framework.test import APIClient

from accounts.models import Role, User
from akademik.models import Penugasan, PeriodeAkademik, TugasAkhir, MilestoneTemplate
from dokumen.models import Dokumen, DokumenVersi
from milestone.services import buat_milestone_untuk_ta
from notifikasi.models import Notifikasi

from .models import ChecklistRevisi, Review

MEDIA_UJI = tempfile.mkdtemp(prefix="simonta-review-tests-")
PASSWORD = "Password-Uji-Review-2026!"


def buat_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@override_settings(
    MEDIA_ROOT=MEDIA_UJI,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class ReviewApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_UJI, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()

        def user(identifier, role, nama):
            return User.objects.create_user(identifier, PASSWORD, role=role, nama_lengkap=nama)

        self.mhs = user("REV-MHS-001", Role.MAHASISWA, "Mahasiswa Review Uji")
        self.mhs_lain = user("REV-MHS-002", Role.MAHASISWA, "Mahasiswa Lain Uji")
        self.utama = user("REV-DSN-001", Role.DOSEN, "Pembimbing Utama Uji")
        self.pendamping = user("REV-DSN-002", Role.DOSEN, "Pembimbing Pendamping Uji")
        self.penguji = user("REV-DSN-003", Role.DOSEN, "Penguji Uji")
        self.dosen_lain = user("REV-DSN-004", Role.DOSEN, "Dosen Lain Uji")

        self.periode = PeriodeAkademik.objects.create(
            label="Periode Review Uji",
            tanggal_mulai=date(2030, 1, 1),
            tanggal_selesai=date(2030, 6, 30),
        )
        for urutan, bobot in enumerate(("30", "30", "40"), start=1):
            MilestoneTemplate.objects.create(
                urutan=urutan, nama=f"Tahap Review Uji {urutan}", bobot=Decimal(bobot)
            )
        self.ta = TugasAkhir.objects.create(
            mahasiswa=self.mhs, periode=self.periode, judul="Judul Tugas Akhir Uji"
        )
        for dosen, peran in (
            (self.utama, Penugasan.Peran.UTAMA),
            (self.pendamping, Penugasan.Peran.PENDAMPING),
            (self.penguji, Penugasan.Peran.PENGUJI),
        ):
            Penugasan.objects.create(tugas_akhir=self.ta, dosen=dosen, peran=peran)
        buat_milestone_untuk_ta(self.ta)
        self.milestone = self.ta.milestone.order_by("urutan").first()
        self.dokumen = Dokumen.objects.create(milestone=self.milestone)
        self.versi = DokumenVersi.objects.create(
            dokumen=self.dokumen,
            nomor_versi=1,
            berkas=SimpleUploadedFile("dokumen-uji.pdf", buat_pdf(), content_type="application/pdf"),
            nama_asli="dokumen-uji.pdf",
            halaman=1,
            ukuran=len(buat_pdf()),
        )

    def simpan_draf(self, user=None, data=None):
        self.client.force_login(user or self.utama)
        return self.client.put(
            f"/api/v1/dosen/review/{self.versi.pk}/draf/",
            data or {},
            format="json",
        )

    def terbitkan(self, review_id):
        return self.client.post(f"/api/v1/dosen/review/{review_id}/terbitkan/", {}, format="json")

    def test_hanya_pembimbing_utama_dan_pendamping_dapat_membuka_detail(self):
        for dosen in (self.utama, self.pendamping):
            self.client.force_login(dosen)
            self.assertEqual(self.client.get(f"/api/v1/dosen/review/{self.versi.pk}/").status_code, 200)
        for dosen in (self.penguji, self.dosen_lain):
            self.client.force_login(dosen)
            self.assertEqual(self.client.get(f"/api/v1/dosen/review/{self.versi.pk}/").status_code, 404)

    def test_detail_dosen_dan_mahasiswa_menyediakan_url_pratinjau_privat(self):
        self.client.force_login(self.utama)
        detail_dosen = self.client.get(f"/api/v1/dosen/review/{self.versi.pk}/")
        self.assertEqual(detail_dosen.status_code, 200)
        self.assertIn("/pratinjau/", detail_dosen.json()["versi"]["pratinjau_url"])

        draft = self.simpan_draf(data={"rekomendasi": "disetujui"}).json()
        self.assertEqual(self.terbitkan(draft["id"]).status_code, 200)
        self.client.force_login(self.mhs)
        detail_mahasiswa = self.client.get(f"/api/v1/mahasiswa/review/{draft['id']}/")
        self.assertEqual(detail_mahasiswa.status_code, 200)
        self.assertIn("/pratinjau/", detail_mahasiswa.json()["versi"]["pratinjau_url"])

    def test_put_draf_membuat_dan_memperbarui_satu_draf(self):
        first = self.simpan_draf(data={"bagian": "Bab 1", "komentar": "Periksa latar belakang"})
        self.assertEqual(first.status_code, 200)
        second = self.simpan_draf(data={"komentar": "Perjelas rumusan masalah"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(Review.objects.filter(versi=self.versi, pemberi=self.utama, status="draf").count(), 1)
        self.assertEqual(second.json()["bagian"], "Bab 1")
        self.assertEqual(second.json()["komentar"], "Perjelas rumusan masalah")

    def test_draf_tidak_terlihat_mahasiswa_dan_catatan_awal_hanya_jika_dibagikan(self):
        draft = self.simpan_draf(data={
            "bagian": "Bab 1",
            "komentar": "Rapikan latar belakang",
            "nilai": 75,
            "rekomendasi": "perlu_revisi",
            "bagikan_catatan_awal": True,
        }).json()
        self.client.force_login(self.mhs)
        list_body = self.client.get("/api/v1/mahasiswa/review/").json()
        self.assertEqual(list_body["hasil"], [])
        note = list_body["menunggu_review"][0]["catatan_awal"]
        self.assertEqual(note["label"], "Bukan review final")
        self.assertEqual(note["komentar"], "Rapikan latar belakang")
        self.assertNotIn("nilai", note)
        self.assertNotIn("rekomendasi", note)
        self.assertNotIn("id", note)
        self.assertEqual(
            self.client.get(f"/api/v1/mahasiswa/review/{draft['id']}/").status_code,
            404,
        )

    def test_dosen_yang_bukan_pemberi_tidak_bisa_mengubah_draf(self):
        result = self.simpan_draf(data={"komentar": "Catatan"})
        draft_id = result.json()["id"]
        self.client.force_login(self.pendamping)
        # Setiap pembimbing memiliki draf sendiri, bukan hak mengubah draf pembimbing lain.
        response = self.terbitkan(draft_id)
        self.assertEqual(response.status_code, 404)

    def test_perlu_revisi_wajib_komentar_dan_penerbitan_mengubah_status_versi(self):
        draft = self.simpan_draf(data={"rekomendasi": "perlu_revisi", "komentar": " "}).json()
        response = self.terbitkan(draft["id"])
        self.assertEqual(response.status_code, 400)
        self.versi.refresh_from_db()
        self.assertEqual(self.versi.status, DokumenVersi.Status.MENUNGGU_REVIEW)
        self.assertEqual(Notifikasi.objects.count(), 0)

        self.simpan_draf(data={"komentar": "Tambahkan referensi pada Bab 1."})
        response = self.terbitkan(draft["id"])
        self.assertEqual(response.status_code, 200)
        self.versi.refresh_from_db()
        self.assertEqual(self.versi.status, DokumenVersi.Status.PERLU_REVISI)
        self.assertEqual(Notifikasi.objects.filter(user=self.mhs, jenis="review_terbit").count(), 1)

    def test_kirim_dua_kali_idempoten_tanpa_review_atau_notifikasi_ganda(self):
        draft = self.simpan_draf(data={"rekomendasi": "disetujui", "nilai": 88}).json()
        first = self.terbitkan(draft["id"])
        second = self.terbitkan(draft["id"])
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(first.json()["sudah_terbit"])
        self.assertTrue(second.json()["sudah_terbit"])
        self.assertEqual(Review.objects.filter(versi=self.versi, pemberi=self.utama).count(), 1)
        self.assertEqual(Notifikasi.objects.filter(user=self.mhs, jenis="review_terbit").count(), 1)
        self.versi.refresh_from_db()
        self.assertEqual(self.versi.status, DokumenVersi.Status.DISETUJUI)

    def test_review_terbit_immutable_dan_koreksi_menjadi_draf_baru(self):
        draft = self.simpan_draf(data={"rekomendasi": "disetujui"}).json()
        self.assertEqual(self.terbitkan(draft["id"]).status_code, 200)
        review = Review.objects.get(pk=draft["id"])
        review.komentar = "Perubahan tidak sah"
        with self.assertRaises(ValueError):
            review.save()
        with self.assertRaises(ValueError):
            review.delete()
        correction = self.simpan_draf(data={"bagian": "Koreksi", "komentar": "Catatan koreksi"})
        self.assertEqual(correction.status_code, 200)
        self.assertNotEqual(correction.json()["id"], draft["id"])

    def test_mahasiswa_hanya_melihat_review_terbit_miliknya(self):
        draft = self.simpan_draf(data={"rekomendasi": "disetujui", "nilai": 90}).json()
        self.client.force_login(self.mhs)
        self.assertEqual(self.client.get("/api/v1/mahasiswa/review/").json()["hasil"], [])
        self.client.force_login(self.utama)
        self.terbitkan(draft["id"])
        self.client.force_login(self.mhs)
        list_response = self.client.get("/api/v1/mahasiswa/review/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()["hasil"]), 1)
        detail = self.client.get(f"/api/v1/mahasiswa/review/{draft['id']}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["review"]["nilai"], 90)
        self.assertEqual(detail.json()["review"]["rekomendasi"], "disetujui")
        self.client.force_login(self.mhs_lain)
        self.assertEqual(self.client.get(f"/api/v1/mahasiswa/review/{draft['id']}/").status_code, 404)

    def test_checklist_crud_pribadi_mahasiswa(self):
        draft = self.simpan_draf(data={"rekomendasi": "perlu_revisi", "komentar": "Perbaiki"}).json()
        self.terbitkan(draft["id"])
        self.client.force_login(self.mhs)
        url = f"/api/v1/mahasiswa/review/{draft['id']}/checklist/"
        created = self.client.post(url, {"catatan": "Tambahkan sumber primer"}, format="json")
        self.assertEqual(created.status_code, 201)
        item_id = created.json()["id"]
        changed = self.client.patch(
            f"/api/v1/mahasiswa/checklist/{item_id}/",
            {"selesai": True, "catatan": "Sumber primer sudah ditambahkan"},
            format="json",
        )
        self.assertEqual(changed.status_code, 200)
        self.assertTrue(changed.json()["selesai"])
        self.client.force_login(self.mhs_lain)
        self.assertEqual(self.client.delete(f"/api/v1/mahasiswa/checklist/{item_id}/").status_code, 404)
        self.client.force_login(self.mhs)
        self.assertEqual(self.client.delete(f"/api/v1/mahasiswa/checklist/{item_id}/").status_code, 204)
        self.assertEqual(ChecklistRevisi.objects.count(), 0)

    def test_nilai_opsional_dibatasi_0_sampai_100(self):
        self.client.force_login(self.utama)
        for nilai in (-1, 101):
            response = self.client.put(
                f"/api/v1/dosen/review/{self.versi.pk}/draf/", {"nilai": nilai}, format="json"
            )
            self.assertEqual(response.status_code, 400)

    def test_penerbitan_review_tidak_mengubah_progress_milestone(self):
        draft = self.simpan_draf(data={"rekomendasi": "disetujui"}).json()
        before = self.milestone.diverifikasi_pada
        self.terbitkan(draft["id"])
        self.milestone.refresh_from_db()
        self.assertEqual(self.milestone.diverifikasi_pada, before)
        self.assertIsNone(self.milestone.diverifikasi_oleh_id)

    def test_antrean_dosen_menampilkan_berkas_unggahan_tertua_dan_pembimbing_berhak(self):
        url = "/api/v1/dosen/review/"
        for dosen in (self.utama, self.pendamping):
            with self.subTest(dosen=dosen.identifier):
                self.client.force_login(dosen)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["jumlah"], 1)
                item = body["hasil"][0]
                self.assertEqual(item["versi"]["id"], self.versi.pk)
                self.assertEqual(item["mahasiswa"]["identifier"], self.mhs.identifier)
                self.assertIsNone(item["draf"])

    def test_antrean_dosen_menandai_draf_milik_dosen_sendiri(self):
        self.simpan_draf(user=self.utama, data={"bagian": "Bab 1", "komentar": "Periksa teori"})
        self.client.force_login(self.utama)
        response = self.client.get("/api/v1/dosen/review/")
        self.assertEqual(response.status_code, 200)
        item = response.json()["hasil"][0]
        self.assertIsNotNone(item["draf"])
        self.assertEqual(response.json()["jumlah_draf"], 1)

        # Draf pembimbing utama tidak mengungkap data draf ke pendamping.
        self.client.force_login(self.pendamping)
        item_pendamping = self.client.get("/api/v1/dosen/review/").json()["hasil"][0]
        self.assertIsNone(item_pendamping["draf"])

    def test_antrean_dosen_hanya_untuk_dosen_pembimbing_dan_hilang_setelah_review_terbit(self):
        url = "/api/v1/dosen/review/"
        self.client.force_login(self.mhs)
        self.assertEqual(self.client.get(url).status_code, 403)
        for dosen in (self.penguji, self.dosen_lain):
            self.client.force_login(dosen)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["hasil"], [])

        draft = self.simpan_draf(user=self.utama, data={"rekomendasi": "disetujui"}).json()
        self.assertEqual(self.terbitkan(draft["id"]).status_code, 200)
        self.client.force_login(self.utama)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["jumlah"], 0)
        self.assertEqual(response.json()["hasil"], [])
