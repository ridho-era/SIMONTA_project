from datetime import date
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory

from accounts.models import Role, User
from akademik.models import KonfigurasiDenda, PeriodeAkademik, Penugasan, TugasAkhir

from .models import CatatanKeterlambatan
from .permissions import IsDosenAtauAdmin
from .services import catatan_boleh_diakses, hitung_denda, simpan_atau_ajukan_keberatan


class HitungDendaTest(SimpleTestCase):
    def test_toleransi_dikurangi_dari_hari_terlambat(self):
        hasil = hitung_denda(
            tenggat=date(2026, 11, 1),
            realisasi=date(2026, 11, 5),
            tarif=10000,
            toleransi=2,
            batas=100000,
        )
        self.assertEqual(hasil["hari_terlambat"], 4)
        self.assertEqual(hasil["hari_dikenai"], 2)
        self.assertEqual(hasil["nominal"], 20000)

    def test_nominal_dibatasi_batas_per_catatan(self):
        hasil = hitung_denda(
            tenggat=date(2026, 11, 1),
            realisasi=date(2026, 11, 12),
            tarif=10000,
            toleransi=1,
            batas=25000,
        )
        self.assertEqual(hasil["hari_dikenai"], 10)
        self.assertEqual(hasil["subtotal"], 100000)
        self.assertEqual(hasil["nominal"], 25000)

    def test_hari_nol_tidak_menghasilkan_denda(self):
        hasil = hitung_denda(
            tenggat=date(2026, 11, 10),
            realisasi=date(2026, 11, 10),
            tarif=10000,
            toleransi=0,
            batas=100000,
        )
        self.assertEqual(hasil["hari_terlambat"], 0)
        self.assertEqual(hasil["hari_dikenai"], 0)
        self.assertEqual(hasil["nominal"], 0)

    def test_format_rumus_memisahkan_argumen_dengan_koma_dan_ribuan_dengan_titik(self):
        hasil = hitung_denda(
            tenggat=date(2026, 11, 11),
            hari_ini=date(2026, 11, 15),
            tarif=5000,
            toleransi=3,
            batas=10000,
        )
        self.assertEqual(
            hasil["rumus"],
            "min(max(4 - 3, 0) × Rp5.000, Rp10.000)",
        )

    def test_perubahan_tenggat_mengubah_hasil_perhitungan(self):
        awal = hitung_denda(
            tenggat=date(2026, 11, 10),
            realisasi=date(2026, 11, 13),
            tarif=5000,
            toleransi=1,
            batas=100000,
        )
        tenggat_baru = hitung_denda(
            tenggat=date(2026, 11, 13),
            realisasi=date(2026, 11, 13),
            tarif=5000,
            toleransi=1,
            batas=100000,
        )
        self.assertEqual(awal["hari_dikenai"], 2)
        self.assertEqual(tenggat_baru["hari_terlambat"], 0)
        self.assertEqual(tenggat_baru["nominal"], 0)


class KeberatanDanIzinTest(TestCase):
    def setUp(self):
        self.mahasiswa = User.objects.create_user(
            identifier="NPM-TEST-1",
            password="test-password-123",
            role=Role.MAHASISWA,
            nama_lengkap="Mahasiswa Pengujian",
        )
        self.dosen_utama = User.objects.create_user(
            identifier="NIP-TEST-1",
            password="test-password-123",
            role=Role.DOSEN,
            nama_lengkap="Dosen Pengujian",
        )
        self.dosen_lain = User.objects.create_user(
            identifier="NIP-TEST-2",
            password="test-password-123",
            role=Role.DOSEN,
            nama_lengkap="Dosen Lain",
        )
        self.admin = User.objects.create_user(
            identifier="ADMIN-TEST",
            password="test-password-123",
            role=Role.ADMIN,
            nama_lengkap="Admin Pengujian",
        )
        self.periode = PeriodeAkademik.objects.create(
            label="Periode Uji",
            tanggal_mulai=date(2026, 7, 1),
            tanggal_selesai=date(2027, 6, 30),
            aktif=True,
        )
        self.tugas_akhir = TugasAkhir.objects.create(
            mahasiswa=self.mahasiswa,
            periode=self.periode,
            judul="Judul pengujian keterlambatan",
        )
        Penugasan.objects.create(
            tugas_akhir=self.tugas_akhir,
            dosen=self.dosen_utama,
            peran=Penugasan.Peran.UTAMA,
        )
        self.konfigurasi = KonfigurasiDenda.objects.create(
            periode=self.periode,
            jenis=KonfigurasiDenda.Jenis.TELAT_BERKAS,
            tarif=5000,
            toleransi_hari=1,
            batas_per_catatan=100000,
        )
        self.catatan = CatatanKeterlambatan.objects.create(
            tugas_akhir=self.tugas_akhir,
            konfigurasi=self.konfigurasi,
            jenis=KonfigurasiDenda.Jenis.TELAT_BERKAS,
            nama_dokumen="Berkas administrasi pengujian",
            tenggat=date(2026, 11, 1),
            realisasi=date(2026, 11, 4),
            tarif=5000,
            toleransi_hari=1,
            batas_per_catatan=100000,
            hari_terlambat=3,
            hari_dikenai=2,
            nominal=10000,
        )

    def test_mahasiswa_tidak_dapat_mengajukan_keberatan_kedua(self):
        simpan_atau_ajukan_keberatan(
            catatan=self.catatan,
            mahasiswa=self.mahasiswa,
            alasan="Keberatan pertama untuk pengujian.",
            aksi="ajukan",
        )
        with self.assertRaises(ValidationError):
            simpan_atau_ajukan_keberatan(
                catatan=self.catatan,
                mahasiswa=self.mahasiswa,
                alasan="Percobaan pengajuan kedua.",
                aksi="ajukan",
            )
        self.assertEqual(self.catatan.keberatan.status, "diajukan")

    def test_izin_objek_mahasiswa_pembimbing_utama_dan_admin(self):
        self.assertTrue(catatan_boleh_diakses(self.mahasiswa, self.catatan))
        self.assertTrue(catatan_boleh_diakses(self.dosen_utama, self.catatan))
        self.assertTrue(catatan_boleh_diakses(self.admin, self.catatan))
        self.assertFalse(catatan_boleh_diakses(self.dosen_lain, self.catatan))

    def test_permission_endpoint_menolak_mahasiswa(self):
        factory = APIRequestFactory()
        request = factory.get("/api/v1/dosen/keterlambatan/")
        request.user = self.mahasiswa
        self.assertFalse(IsDosenAtauAdmin().has_permission(request, None))

    def test_permission_endpoint_menerima_dosen_aktif(self):
        factory = APIRequestFactory()
        request = factory.get("/api/v1/dosen/keterlambatan/")
        request.user = self.dosen_utama
        self.assertTrue(IsDosenAtauAdmin().has_permission(request, None))

    def test_permission_endpoint_menolak_akun_wajib_ganti_password(self):
        factory = APIRequestFactory()
        request = factory.get("/api/v1/dosen/keterlambatan/")
        user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            must_change_password=True,
            role=Role.DOSEN,
        )
        request.user = user
        self.assertFalse(IsDosenAtauAdmin().has_permission(request, None))
