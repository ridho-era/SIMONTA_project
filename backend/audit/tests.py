from unittest import mock

from django.contrib.admin.sites import site
from django.forms.models import inlineformset_factory
from django.test import RequestFactory, TestCase, override_settings

from accounts.admin import UserAdmin
from accounts.models import Role, User
from akademik.admin import JenisSanksiAdmin, PenugasanInlineFormSet, TugasAkhirAdmin
from akademik.models import JenisSanksi, Penugasan, PeriodeAkademik, TugasAkhir

from .admin import AuditLogAdmin
from .models import AuditLog

FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
PASSWORD = "Sandi-Uji-12345!"  # data uji sintetis


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class AuditBase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            "TEST-SUPER-001", PASSWORD, nama_lengkap="Admin Uji Palsu"
        )
        self.request = RequestFactory().post("/")
        self.request.user = self.admin_user


class AuditMixinTests(AuditBase):
    def setUp(self):
        super().setUp()
        self.ma = JenisSanksiAdmin(JenisSanksi, site)

    def test_tambah_tercatat(self):
        obj = JenisSanksi(nama="Sanksi Uji A")
        self.ma.save_model(self.request, obj, None, False)
        log = AuditLog.objects.get()
        self.assertEqual(log.aksi, "tambah")
        self.assertEqual(log.objek_tipe, "akademik.JenisSanksi")
        self.assertEqual(log.objek_id, str(obj.pk))
        self.assertIsNone(log.sebelum)
        self.assertEqual(log.sesudah["nama"], "Sanksi Uji A")
        self.assertEqual(log.aktor, self.admin_user)
        self.assertEqual(log.aktor_identifier, "TEST-SUPER-001")

    def test_ubah_hanya_mencatat_field_yang_berubah(self):
        obj = JenisSanksi.objects.create(nama="Sanksi Uji A")
        obj.nama = "Sanksi Uji B"
        self.ma.save_model(self.request, obj, None, True)
        log = AuditLog.objects.get()
        self.assertEqual(log.aksi, "ubah")
        self.assertEqual(log.sebelum, {"nama": "Sanksi Uji A"})
        self.assertEqual(log.sesudah, {"nama": "Sanksi Uji B"})

    def test_simpan_tanpa_perubahan_tidak_dicatat(self):
        obj = JenisSanksi.objects.create(nama="Sanksi Uji A")
        self.ma.save_model(self.request, obj, None, True)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_hapus_tercatat_dengan_id_asli(self):
        obj = JenisSanksi.objects.create(nama="Sanksi Uji A")
        pk = obj.pk
        self.ma.delete_model(self.request, obj)
        log = AuditLog.objects.get()
        self.assertEqual(log.aksi, "hapus")
        self.assertEqual(log.objek_id, str(pk))
        self.assertEqual(log.sebelum["nama"], "Sanksi Uji A")
        self.assertIsNone(log.sesudah)

    def test_hapus_massal_tercatat(self):
        JenisSanksi.objects.create(nama="Sanksi Uji A")
        JenisSanksi.objects.create(nama="Sanksi Uji B")
        self.ma.delete_queryset(self.request, JenisSanksi.objects.all())
        self.assertEqual(JenisSanksi.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(aksi="hapus").count(), 2)

    def test_audit_log_tidak_dapat_diubah(self):
        obj = JenisSanksi(nama="Sanksi Uji A")
        self.ma.save_model(self.request, obj, None, False)
        log = AuditLog.objects.get()
        log.keterangan = "dimanipulasi"
        with self.assertRaises(ValueError):
            log.save()

    def test_audit_log_admin_hanya_baca(self):
        ma = AuditLogAdmin(AuditLog, site)
        self.assertFalse(ma.has_add_permission(self.request))
        self.assertFalse(ma.has_change_permission(self.request))
        self.assertFalse(ma.has_delete_permission(self.request))


class AuditAkademikTests(AuditBase):
    def setUp(self):
        super().setUp()
        self.mhs = User.objects.create_user(
            "TEST-MHS-001", PASSWORD, role=Role.MAHASISWA, nama_lengkap="Mahasiswa Uji Palsu"
        )
        self.dosen = User.objects.create_user(
            "TEST-DSN-001", PASSWORD, role=Role.DOSEN, nama_lengkap="Dosen Uji Palsu"
        )
        periode = PeriodeAkademik(
            label="Periode Uji", tanggal_mulai="2030-01-01", tanggal_selesai="2030-06-30"
        )
        periode.save()
        self.ta = TugasAkhir.objects.create(
            mahasiswa=self.mhs, periode=periode, judul="Judul Uji Palsu"
        )
        self.ma = TugasAkhirAdmin(TugasAkhir, site)
        self.FormSet = inlineformset_factory(
            TugasAkhir,
            Penugasan,
            formset=PenugasanInlineFormSet,
            fields=("dosen", "peran"),
            extra=0,
        )

    def test_kolom_penjaga_tidak_masuk_log(self):
        self.ta.status = TugasAkhir.Status.SELESAI
        self.ma.save_model(self.request, self.ta, None, True)
        log = AuditLog.objects.get()
        self.assertEqual(log.sebelum, {"status": "aktif"})
        self.assertEqual(log.sesudah, {"status": "selesai"})

    def test_inline_penugasan_tambah_dan_hapus_tercatat(self):
        data = {
            "penugasan-TOTAL_FORMS": "1",
            "penugasan-INITIAL_FORMS": "0",
            "penugasan-MIN_NUM_FORMS": "0",
            "penugasan-MAX_NUM_FORMS": "1000",
            "penugasan-0-dosen": str(self.dosen.pk),
            "penugasan-0-peran": "utama",
        }
        formset = self.FormSet(data=data, instance=self.ta)
        self.assertTrue(formset.is_valid(), formset.errors)
        self.ma.save_formset(self.request, None, formset, False)
        penugasan = Penugasan.objects.get()
        log = AuditLog.objects.get(objek_tipe="akademik.Penugasan")
        self.assertEqual(log.aksi, "tambah")
        self.assertEqual(log.sesudah["peran"], "utama")

        data_hapus = {
            "penugasan-TOTAL_FORMS": "1",
            "penugasan-INITIAL_FORMS": "1",
            "penugasan-MIN_NUM_FORMS": "0",
            "penugasan-MAX_NUM_FORMS": "1000",
            "penugasan-0-id": str(penugasan.pk),
            "penugasan-0-tugas_akhir": str(self.ta.pk),
            "penugasan-0-dosen": str(self.dosen.pk),
            "penugasan-0-peran": "utama",
            "penugasan-0-DELETE": "on",
        }
        formset = self.FormSet(data=data_hapus, instance=self.ta)
        self.assertTrue(formset.is_valid(), formset.errors)
        self.ma.save_formset(self.request, None, formset, True)
        self.assertEqual(Penugasan.objects.count(), 0)
        self.assertTrue(
            AuditLog.objects.filter(objek_tipe="akademik.Penugasan", aksi="hapus").exists()
        )


class AuditAkunTests(AuditBase):
    def test_password_tidak_pernah_masuk_log(self):
        ma = UserAdmin(User, site)
        user = User(identifier="TEST-MHS-009", role=Role.MAHASISWA, nama_lengkap="Uji Palsu")
        user.set_password(PASSWORD)
        ma.save_model(self.request, user, None, False)
        log = AuditLog.objects.get(objek_tipe="accounts.User")
        self.assertEqual(log.sesudah["identifier"], "TEST-MHS-009")
        self.assertNotIn("password", log.sesudah)
        self.assertTrue(log.sesudah["must_change_password"])

    def test_reset_password_tercatat_tanpa_membocorkan_password(self):
        user = User.objects.create_user(
            "TEST-MHS-010", PASSWORD, role=Role.MAHASISWA, nama_lengkap="Uji Palsu"
        )
        ma = UserAdmin(User, site)
        with mock.patch.object(UserAdmin, "message_user"):
            ma.reset_password_sementara(self.request, User.objects.filter(pk=user.pk))
        user.refresh_from_db()
        self.assertTrue(user.must_change_password)
        self.assertFalse(user.check_password(PASSWORD))
        log = AuditLog.objects.get(aksi="reset_password")
        self.assertEqual(log.objek_id, str(user.pk))
        self.assertNotIn("password", (log.keterangan or "").lower().replace("password sementara", ""))