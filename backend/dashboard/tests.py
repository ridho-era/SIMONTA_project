from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.test import TestCase, override_settings
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APIClient

from accounts.models import Role, User
from akademik.models import (
    KonfigurasiDenda,
    MilestoneTemplate,
    Penugasan,
    PeriodeAkademik,
    TugasAkhir,
)
from dokumen.models import Dokumen, DokumenVersi
from milestone.models import Milestone
from milestone.services import buat_milestone_untuk_ta
from keterlambatan.models import CatatanKeterlambatan
from review.models import Review

PASSWORD = "Sandi-Uji-12345!"
URL_MHS = "/api/v1/mahasiswa/dashboard/"
URL_DSN = "/api/v1/dosen/dashboard/"
URL_DAFTAR = "/api/v1/dosen/mahasiswa/"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DashboardDanMahasiswaBimbinganTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user("TEST-ADMIN", PASSWORD, role=Role.ADMIN, nama_lengkap="Admin Uji")
        self.dosen = User.objects.create_user("TEST-DSN-001", PASSWORD, role=Role.DOSEN, nama_lengkap="Dosen Utama Uji")
        self.pendamping = User.objects.create_user("TEST-DSN-002", PASSWORD, role=Role.DOSEN, nama_lengkap="Dosen Pendamping Uji")
        self.penguji = User.objects.create_user("TEST-DSN-003", PASSWORD, role=Role.DOSEN, nama_lengkap="Dosen Penguji Uji")
        self.dosen_lain = User.objects.create_user("TEST-DSN-004", PASSWORD, role=Role.DOSEN, nama_lengkap="Dosen Lain Uji")
        self.mahasiswa = self.buat_mahasiswa(1, "Ani Mahasiswa Uji")
        self.mahasiswa_lain = self.buat_mahasiswa(2, "Budi Mahasiswa Uji")
        self.periode = PeriodeAkademik.objects.create(
            label="Periode Uji Dashboard",
            tanggal_mulai=date(2030, 1, 1),
            tanggal_selesai=date(2030, 12, 31),
        )
        self.template = [
            MilestoneTemplate.objects.create(urutan=1, nama="Bab 1 Uji", bobot=Decimal("60")),
            MilestoneTemplate.objects.create(urutan=2, nama="Bab 2 Uji", bobot=Decimal("40")),
        ]
        self.ta = self.buat_ta(self.mahasiswa, self.dosen, "Judul TA Ani Uji")
        self.ta_lain = self.buat_ta(self.mahasiswa_lain, self.pendamping, "Judul TA Budi Uji")

    def buat_mahasiswa(self, nomor, nama):
        return User.objects.create_user(
            f"TEST-MHS-{nomor:03d}", PASSWORD, role=Role.MAHASISWA, nama_lengkap=nama
        )

    def buat_ta(self, mahasiswa, dosen, judul, peran=Penugasan.Peran.UTAMA):
        ta = TugasAkhir.objects.create(mahasiswa=mahasiswa, periode=self.periode, judul=judul)
        Penugasan.objects.create(tugas_akhir=ta, dosen=dosen, peran=peran)
        buat_milestone_untuk_ta(ta)
        return ta

    def buat_catatan_keterlambatan(self, ta, *, status=CatatanKeterlambatan.StatusPenilaian.USULAN, nama="Berkas administrasi uji"):
        konfigurasi, _ = KonfigurasiDenda.objects.get_or_create(
            periode=ta.periode,
            jenis=KonfigurasiDenda.Jenis.TELAT_BERKAS,
            defaults={"tarif": 5000, "toleransi_hari": 3, "batas_per_catatan": 10000},
        )
        return CatatanKeterlambatan.objects.create(
            tugas_akhir=ta,
            konfigurasi=konfigurasi,
            jenis=KonfigurasiDenda.Jenis.TELAT_BERKAS,
            nama_dokumen=nama,
            tenggat=timezone.localdate() - timedelta(days=4),
            tarif=5000,
            toleransi_hari=3,
            batas_per_catatan=10000,
            hari_terlambat=4,
            hari_dikenai=1,
            nominal=5000,
            status_penilaian=status,
        )

    def buat_versi(self, ta, nama="berkas-uji.pdf", status=DokumenVersi.Status.MENUNGGU_REVIEW):
        milestone = ta.milestone.order_by("urutan").first()
        dokumen, _ = Dokumen.objects.get_or_create(milestone=milestone)
        return DokumenVersi.objects.create(
            dokumen=dokumen,
            nomor_versi=1,
            berkas="dokumen/berkas-uji.pdf",
            nama_asli=nama,
            halaman=2,
            ukuran=2048,
            status=status,
        )

    # --- akses dan dashboard mahasiswa ---
    def test_dashboard_mahasiswa_hanya_membaca_data_sendiri(self):
        milestone = self.ta.milestone.order_by("urutan").first()
        Milestone.objects.filter(pk=milestone.pk).update(
            tingkat_penyelesaian=75,
            diverifikasi_oleh=self.dosen,
            diverifikasi_pada=timezone.now(),
        )
        self.client.force_login(self.mahasiswa)
        response = self.client.get(URL_MHS)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["tugas_akhir"]["id"], self.ta.pk)
        self.assertEqual(body["progres"], 45.0)
        self.assertEqual(body["jumlah_diverifikasi"], 1)
        self.assertEqual(body["tahap_aktif"]["nama"], "Bab 2 Uji")
        self.assertEqual(body["tim_pembimbing"][0]["identifier"], self.dosen.identifier)
        self.assertIsNone(body["bimbingan_terdekat"])
        self.assertIsNone(body["ringkasan_denda"])

    def test_dashboard_mahasiswa_menampilkan_banner_milestone_terlambat(self):
        milestone = self.ta.milestone.order_by("urutan").first()
        tenggat = timezone.localdate() - timedelta(days=1)
        Milestone.objects.filter(pk=milestone.pk).update(target=tenggat)
        self.client.force_login(self.mahasiswa)
        body = self.client.get(URL_MHS).json()
        self.assertEqual(body["banner_keterlambatan"]["milestone"]["nama"], "Bab 1 Uji")
        self.assertEqual(body["banner_keterlambatan"]["target"], tenggat.isoformat())
        self.assertIsNone(body["banner_keterlambatan"]["sanksi_akademik"])

    def test_dashboard_mahasiswa_menampilkan_empty_state_tanpa_ta(self):
        baru = self.buat_mahasiswa(9, "Mahasiswa Tanpa TA Uji")
        self.client.force_login(baru)
        body = self.client.get(URL_MHS).json()
        self.assertIsNone(body["tugas_akhir"])
        self.assertEqual(body["progres"], 0)
        self.assertEqual(body["tim_pembimbing"], [])
        self.assertIsNone(body["review_tindak_lanjut"])
        self.assertIsNone(body["banner_keterlambatan"])

    def test_dashboard_hanya_mengambil_review_terbit_perlu_revisi(self):
        versi = self.buat_versi(self.ta, status=DokumenVersi.Status.PERLU_REVISI)
        Review.objects.create(
            versi=versi, pemberi=self.dosen, status=Review.Status.DRAF,
            komentar="Draf rahasia", rekomendasi=Review.Rekomendasi.PERLU_REVISI,
        )
        self.client.force_login(self.mahasiswa)
        self.assertIsNone(self.client.get(URL_MHS).json()["review_tindak_lanjut"])

        Review.objects.create(
            versi=versi, pemberi=self.pendamping, status=Review.Status.TERBIT,
            komentar="Mohon perbaiki bagian metode.", rekomendasi=Review.Rekomendasi.PERLU_REVISI,
        )
        body = self.client.get(URL_MHS).json()
        self.assertEqual(body["review_tindak_lanjut"]["pemberi"], self.pendamping.nama_lengkap)
        self.assertNotIn("Draf rahasia", str(body["review_tindak_lanjut"]))

    def test_dashboard_mahasiswa_hanya_bisa_diakses_mahasiswa(self):
        self.client.force_login(self.dosen)
        self.assertEqual(self.client.get(URL_MHS).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(URL_MHS).status_code, 403)

    # --- dashboard dosen ---
    def test_dashboard_dosen_menghitung_mahasiswa_menunggu_dan_terlambat(self):
        self.buat_versi(self.ta)
        milestone_budi = self.ta_lain.milestone.order_by("urutan").first()
        Milestone.objects.filter(pk=milestone_budi.pk).update(target=timezone.localdate() - timedelta(days=1))
        self.client.force_login(self.dosen)
        body = self.client.get(URL_DSN).json()
        self.assertEqual(body["statistik"]["mahasiswa_bimbingan"], 1)
        self.assertEqual(body["statistik"]["menunggu_review"], 1)
        self.assertEqual(body["statistik"]["terlambat"], 0)
        self.assertEqual(body["antrean_review"]["jumlah"], 1)
        self.assertEqual(body["perlu_perhatian"], [])

        self.client.force_login(self.pendamping)
        body = self.client.get(URL_DSN).json()
        self.assertEqual(body["statistik"]["mahasiswa_bimbingan"], 1)
        self.assertEqual(body["statistik"]["terlambat"], 1)
        self.assertEqual(body["perlu_perhatian"][0]["mahasiswa"]["id"], self.mahasiswa_lain.pk)

    def test_dashboard_dosen_menghitung_catatan_berkas_aktif(self):
        self.buat_catatan_keterlambatan(self.ta)
        self.client.force_login(self.dosen)

        body = self.client.get(URL_DSN).json()

        self.assertEqual(body["statistik"]["terlambat"], 1)

    def test_dashboard_dosen_menghitung_mahasiswa_unik_dari_beberapa_catatan(self):
        self.buat_catatan_keterlambatan(self.ta, nama="Berkas pertama")
        self.buat_catatan_keterlambatan(
            self.ta,
            status=CatatanKeterlambatan.StatusPenilaian.DITETAPKAN,
            nama="Berkas kedua",
        )
        self.client.force_login(self.dosen)

        body = self.client.get(URL_DSN).json()

        self.assertEqual(body["statistik"]["terlambat"], 1)

    def test_dashboard_dosen_mengabaikan_catatan_yang_dibatalkan(self):
        self.buat_catatan_keterlambatan(
            self.ta,
            status=CatatanKeterlambatan.StatusPenilaian.DIBATALKAN,
        )
        self.client.force_login(self.dosen)

        body = self.client.get(URL_DSN).json()

        self.assertEqual(body["statistik"]["terlambat"], 0)

    def test_dashboard_dosen_tidak_menghitung_catatan_ta_yang_bukan_bimbingan_utama(self):
        self.buat_catatan_keterlambatan(self.ta_lain)
        self.client.force_login(self.dosen)

        body = self.client.get(URL_DSN).json()

        self.assertEqual(body["statistik"]["terlambat"], 0)

    def test_dashboard_dosen_menggabungkan_milestone_dan_catatan_tanpa_duplikasi(self):
        milestone = self.ta.milestone.order_by("urutan").first()
        Milestone.objects.filter(pk=milestone.pk).update(
            target=timezone.localdate() - timedelta(days=1)
        )
        self.buat_catatan_keterlambatan(self.ta)
        self.client.force_login(self.dosen)

        body = self.client.get(URL_DSN).json()

        self.assertEqual(body["statistik"]["terlambat"], 1)

    def test_tugas_akhir_selesai_tidak_masuk_status_terlambat(self):
        milestone = self.ta.milestone.order_by("urutan").first()
        Milestone.objects.filter(pk=milestone.pk).update(target=timezone.localdate() - timedelta(days=1))
        TugasAkhir.objects.filter(pk=self.ta.pk).update(
            status=TugasAkhir.Status.SELESAI,
            slot_aktif=None,
        )
        self.client.force_login(self.dosen)
        body = self.client.get(URL_DSN).json()
        self.assertEqual(body["statistik"]["terlambat"], 0)
        daftar = self.client.get(URL_DAFTAR).json()
        self.assertEqual(daftar["hasil"][0]["status"], "selesai")

    def test_dashboard_dosen_tidak_menghitung_pengujian_sebagai_bimbingan(self):
        Penugasan.objects.create(tugas_akhir=self.ta, dosen=self.penguji, peran=Penugasan.Peran.PENGUJI)
        self.client.force_login(self.penguji)
        body = self.client.get(URL_DSN).json()
        self.assertEqual(body["statistik"]["mahasiswa_bimbingan"], 0)
        self.assertEqual(body["antrean_review"]["jumlah"], 0)

    def test_dashboard_dosen_hanya_bisa_diakses_dosen(self):
        self.client.force_login(self.mahasiswa)
        self.assertEqual(self.client.get(URL_DSN).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(URL_DSN).status_code, 403)

    # --- daftar mahasiswa bimbingan ---
    def test_daftar_hanya_memuat_mahasiswa_yang_ditugaskan_kepada_dosen(self):
        ta_asing = self.buat_ta(
            self.buat_mahasiswa(3, "Mahasiswa Dosen Lain Uji"), self.dosen_lain, "TA Dosen Lain Uji"
        )
        self.buat_ta(
            self.buat_mahasiswa(4, "Mahasiswa Penguji Uji"), self.penguji, "TA Penguji Uji",
            peran=Penugasan.Peran.PENGUJI,
        )
        self.client.force_login(self.dosen)
        body = self.client.get(URL_DAFTAR).json()
        self.assertEqual(body["jumlah"], 1)
        self.assertEqual([item["mahasiswa"]["id"] for item in body["hasil"]], [self.mahasiswa.pk])
        self.assertNotIn(ta_asing.mahasiswa_id, [item["mahasiswa"]["id"] for item in body["hasil"]])

    def test_pembimbing_pendamping_dapat_melihat_tetapi_tidak_mengelola_milestone(self):
        Penugasan.objects.create(
            tugas_akhir=self.ta,
            dosen=self.pendamping,
            peran=Penugasan.Peran.PENDAMPING,
        )
        self.client.force_login(self.pendamping)
        body = self.client.get(URL_DAFTAR).json()
        self.assertEqual(body["jumlah"], 2)
        baris_ani = next(item for item in body["hasil"] if item["mahasiswa"]["id"] == self.mahasiswa.pk)
        self.assertTrue(baris_ani["can_review"])
        self.assertFalse(baris_ani["can_manage_milestone"])

    def test_filter_pencarian_status_milestone_dan_tab(self):
        versi = self.buat_versi(self.ta)
        milestone = self.ta_lain.milestone.order_by("urutan").first()
        Milestone.objects.filter(pk=milestone.pk).update(target=timezone.localdate() - timedelta(days=1))
        self.client.force_login(self.dosen)

        menunggu = self.client.get(URL_DAFTAR, {"tab": "menunggu_review"}).json()
        self.assertEqual(menunggu["jumlah"], 1)
        self.assertEqual(menunggu["hasil"][0]["mahasiswa"]["id"], self.mahasiswa.pk)

        terlambat = self.client.get(URL_DAFTAR, {"tab": "terlambat"}).json()
        self.assertEqual(terlambat["jumlah"], 0)  # TA yang terlambat ditugaskan kepada pendamping.

        self.client.force_login(self.pendamping)
        terlambat = self.client.get(URL_DAFTAR, {"tab": "terlambat"}).json()
        self.assertEqual(terlambat["jumlah"], 1)
        self.assertEqual(terlambat["hasil"][0]["status"], "terlambat")

        cari = self.client.get(URL_DAFTAR, {"q": "Budi"}).json()
        self.assertEqual(cari["jumlah"], 1)
        cari_npm = self.client.get(URL_DAFTAR, {"q": self.mahasiswa_lain.identifier}).json()
        self.assertEqual(cari_npm["jumlah"], 1)
        self.assertEqual(cari_npm["hasil"][0]["mahasiswa"]["id"], self.mahasiswa_lain.pk)
        filter_ms = self.client.get(URL_DAFTAR, {"milestone": milestone.pk}).json()
        self.assertEqual(filter_ms["jumlah"], 1)
        self.assertEqual(filter_ms["hasil"][0]["id"], self.ta_lain.pk)
        self.assertEqual(self.client.get(URL_DAFTAR, {"status": "status_tidak_valid"}).status_code, 400)
        self.assertEqual(self.client.get(URL_DAFTAR, {"milestone": "bukan-angka"}).status_code, 400)
        self.assertIsNotNone(versi.pk)

    def test_filter_status_dan_urutan_diterapkan_di_server(self):
        milestone = self.ta_lain.milestone.order_by("urutan").first()
        Milestone.objects.filter(pk=milestone.pk).update(target=timezone.localdate() - timedelta(days=1))
        self.client.force_login(self.pendamping)
        status_late = self.client.get(URL_DAFTAR, {"status": "terlambat"}).json()
        self.assertEqual(status_late["jumlah"], 1)
        self.assertEqual(status_late["hasil"][0]["status"], "terlambat")
        desc = self.client.get(URL_DAFTAR, {"urut": "nama", "arah": "desc"}).json()
        self.assertEqual(desc["hasil"][0]["mahasiswa"]["nama_lengkap"], "Budi Mahasiswa Uji")
        self.assertEqual(self.client.get(URL_DAFTAR, {"urut": "tidak-valid"}).status_code, 400)

    def test_paginasi_menggunakan_dua_puluh_baris(self):
        for nomor in range(10, 32):
            mhs = self.buat_mahasiswa(nomor, f"Mahasiswa Paginasi {nomor:03d}")
            self.buat_ta(mhs, self.dosen, f"Judul Paginasi {nomor:03d}")
        self.client.force_login(self.dosen)
        pertama = self.client.get(URL_DAFTAR).json()
        kedua = self.client.get(URL_DAFTAR, {"halaman": 2}).json()
        self.assertEqual(pertama["jumlah"], 23)
        self.assertEqual((len(pertama["hasil"]), pertama["halaman"], pertama["total_halaman"]), (20, 1, 2))
        self.assertEqual((len(kedua["hasil"]), kedua["halaman"]), (3, 2))

    def test_ekspor_csv_dan_xlsx_mengikuti_filter(self):
        self.buat_versi(self.ta)
        self.client.force_login(self.dosen)
        csv_response = self.client.get(URL_DAFTAR, {"q": "Ani", "tab": "menunggu_review", "ekspor": "csv"})
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("text/csv", csv_response["Content-Type"])
        self.assertIn("Ani Mahasiswa Uji", csv_response.content.decode("utf-8-sig"))
        self.assertNotIn("Budi Mahasiswa Uji", csv_response.content.decode("utf-8-sig"))

        xlsx_response = self.client.get(URL_DAFTAR, {"q": "Ani", "tab": "menunggu_review", "ekspor": "xlsx"})
        self.assertEqual(xlsx_response.status_code, 200)
        workbook = load_workbook(BytesIO(xlsx_response.content), read_only=True)
        rows = list(workbook.active.values)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], "Ani Mahasiswa Uji")
        self.assertEqual(self.client.get(URL_DAFTAR, {"ekspor": "pdf"}).status_code, 400)

    def test_daftar_mahasiswa_bimbingan_hanya_bisa_diakses_dosen(self):
        self.client.force_login(self.mahasiswa)
        self.assertEqual(self.client.get(URL_DAFTAR).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(URL_DAFTAR).status_code, 403)