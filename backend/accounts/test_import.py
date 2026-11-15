import csv
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from accounts.models import Role, User
from audit.models import AuditLog

FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
HEADER = "identifier,nama_lengkap,role,email_akademik,telepon\n"


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class ImportPenggunaTests(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.keluaran = self.dir / "hasil.csv"

    def tulis(self, isi, nama="uji.csv"):
        path = self.dir / nama
        path.write_text(isi, encoding="utf-8-sig", newline="")
        return path

    def jalankan(self, path, **opsi):
        out = StringIO()
        call_command(
            "import_pengguna",
            str(path),
            keluaran=str(self.keluaran),
            stdout=out,
            no_color=True,
            **opsi,
        )
        return out.getvalue()

    def test_impor_berhasil_membuat_akun_dan_password_sementara(self):
        path = self.tulis(
            HEADER
            + "TEST-IMP-001,Mahasiswa Impor Palsu,mahasiswa,imp001@example.test,0800000001\n"
            + "TEST-IMP-002,Dosen Impor Palsu,Dosen,,\n"
        )
        out = self.jalankan(path)
        self.assertIn("Berhasil: 2", out)

        mhs = User.objects.get(identifier="TEST-IMP-001")
        self.assertEqual(mhs.role, Role.MAHASISWA)
        self.assertEqual(mhs.email_akademik, "imp001@example.test")
        self.assertTrue(mhs.must_change_password)
        dosen = User.objects.get(identifier="TEST-IMP-002")
        self.assertEqual(dosen.role, Role.DOSEN)  # "Dosen" dinormalkan ke huruf kecil
        self.assertIsNone(dosen.email_akademik)

        with self.keluaran.open(encoding="utf-8-sig", newline="") as f:
            hasil = {r["identifier"]: r["password_sementara"] for r in csv.DictReader(f)}
        self.assertTrue(mhs.check_password(hasil["TEST-IMP-001"]))
        self.assertTrue(dosen.check_password(hasil["TEST-IMP-002"]))

        log = AuditLog.objects.filter(aksi="tambah", objek_tipe="accounts.User")
        self.assertEqual(log.count(), 2)
        self.assertTrue(all(entri.aktor is None for entri in log))
        self.assertTrue(all("password" not in entri.sesudah for entri in log))

    def test_baris_gagal_dilaporkan_dan_baris_valid_tetap_masuk(self):
        User.objects.create_user(
            "TEST-IMP-099", "Sandi-Uji-12345!", role=Role.DOSEN, nama_lengkap="Sudah Ada Palsu"
        )
        path = self.tulis(
            HEADER
            + "TEST-IMP-001,Mahasiswa Valid Palsu,mahasiswa,,\n"          # baris 2: valid
            + "TEST-IMP-001,Duplikat Palsu,mahasiswa,,\n"                  # baris 3: duplikat di berkas
            + "TEST-IMP-002,Role Salah Palsu,admin,,\n"                    # baris 4: role tidak diizinkan
            + "TEST-IMP-003,Email Salah Palsu,mahasiswa,bukan-email,\n"    # baris 5: email tidak valid
            + "TEST-IMP-004,,mahasiswa,,\n"                                # baris 6: nama kosong
            + "TEST-IMP-005,Mahasiswa Valid Dua,mahasiswa,,\n"             # baris 7: valid
            + "TEST-IMP-099,Sudah Ada Lagi,dosen,,\n"                      # baris 8: sudah di database
        )
        out = self.jalankan(path)
        self.assertIn("Berhasil: 2", out)
        self.assertIn("Gagal: 5", out)
        for nomor in (3, 4, 5, 6, 8):
            self.assertIn(f"Baris {nomor} ", out)
        self.assertEqual(
            set(
                User.objects.filter(identifier__startswith="TEST-IMP-0").values_list(
                    "identifier", flat=True
                )
            ),
            {"TEST-IMP-001", "TEST-IMP-005", "TEST-IMP-099"},
        )

    def test_email_duplikat_di_berkas_ditolak(self):
        path = self.tulis(
            HEADER
            + "TEST-IMP-001,Satu Palsu,mahasiswa,sama@example.test,\n"
            + "TEST-IMP-002,Dua Palsu,mahasiswa,SAMA@example.test,\n"
        )
        out = self.jalankan(path)
        self.assertIn("Berhasil: 1", out)
        self.assertIn("Baris 3 ", out)

    def test_dry_run_tidak_menulis_apa_pun(self):
        path = self.tulis(HEADER + "TEST-IMP-001,Mahasiswa Impor Palsu,mahasiswa,,\n")
        out = self.jalankan(path, dry_run=True)
        self.assertIn("Valid: 1", out)
        self.assertEqual(User.objects.count(), 0)
        self.assertFalse(self.keluaran.exists())
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_pemisah_titik_koma_dikenali(self):
        path = self.tulis(
            "identifier;nama_lengkap;role;email_akademik;telepon\n"
            "TEST-IMP-001;Mahasiswa Impor Palsu;mahasiswa;;\n"
        )
        out = self.jalankan(path)
        self.assertIn("Berhasil: 1", out)

    def test_kolom_wajib_hilang_menghentikan_impor(self):
        path = self.tulis("identifier,nama_lengkap\nTEST-IMP-001,Mahasiswa Impor Palsu\n")
        with self.assertRaises(CommandError):
            self.jalankan(path)
        self.assertEqual(User.objects.count(), 0)

    def test_berkas_tidak_ada(self):
        with self.assertRaises(CommandError):
            self.jalankan(self.dir / "tidak-ada.csv")

    def test_baris_kosong_dilewati(self):
        path = self.tulis(HEADER + ",,,,\nTEST-IMP-001,Mahasiswa Impor Palsu,mahasiswa,,\n")
        out = self.jalankan(path)
        self.assertIn("Total baris data: 1", out)
        self.assertIn("Berhasil: 1", out)