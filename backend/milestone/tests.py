from datetime import date, timedelta
from decimal import Decimal

from django.contrib.admin.sites import site
from django.core.exceptions import ValidationError
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Role, User
from akademik.admin import TugasAkhirAdmin, TugasAkhirForm
from akademik.models import MilestoneTemplate, Penugasan, PeriodeAkademik, TugasAkhir
from audit.models import AuditLog
from notifikasi.models import Notifikasi

from .models import Milestone
from .services import Status, bangun_timeline, buat_milestone_untuk_ta, hitung_progres

PASSWORD = "Sandi-Uji-12345!"  # semua data sintetis dan jelas palsu
HARI_INI = date(2030, 3, 15)
MHS_URL = "/api/v1/mahasiswa/milestone/"


def url_target(pk):
    return f"/api/v1/dosen/milestone/{pk}/target/"


def url_verif(pk):
    return f"/api/v1/dosen/milestone/{pk}/verifikasi/"


class ProgresDanStatusTests(SimpleTestCase):
    def m(self, urutan, bobot, target=None, tingkat=0, verif=False):
        return Milestone(
            id=urutan, tugas_akhir_id=1, urutan=urutan, nama=f"Tahap Uji {urutan}",
            bobot=Decimal(bobot), target=target, tingkat_penyelesaian=tingkat,
            diverifikasi_pada=timezone.now() if verif else None,
        )

    def test_progres_hanya_menghitung_yang_terverifikasi(self):
        daftar = [self.m(1, "30", tingkat=100, verif=True), self.m(2, "30", tingkat=50, verif=True), self.m(3, "40", tingkat=100)]
        self.assertEqual(hitung_progres(daftar), Decimal("45.00"))

    def test_progres_nol_dan_penuh(self):
        self.assertEqual(hitung_progres([self.m(1, "60", tingkat=100), self.m(2, "40", tingkat=100)]), Decimal("0.00"))
        penuh = [self.m(1, "60", tingkat=100, verif=True), self.m(2, "40", tingkat=100, verif=True)]
        self.assertEqual(hitung_progres(penuh), Decimal("100.00"))

    def test_tahap_aktif_adalah_yang_pertama_belum_diverifikasi(self):
        tl = bangun_timeline([self.m(1, "50", tingkat=100, verif=True), self.m(2, "30"), self.m(3, "20")], HARI_INI)
        self.assertEqual(tl.tahap_aktif_id, 2)
        self.assertEqual([i.tahap_aktif for i in tl.items], [False, True, False])
        self.assertEqual(tl.jumlah_diverifikasi, 1)

    def test_status_sesuai_br02(self):
        tl = bangun_timeline(
            [
                self.m(1, "25", target=HARI_INI - timedelta(days=30), tingkat=100, verif=True),
                self.m(2, "25", target=HARI_INI - timedelta(days=1)),
                self.m(3, "25", target=HARI_INI + timedelta(days=10)),
                self.m(4, "25"),
            ],
            HARI_INI,
        )
        self.assertEqual(
            [i.status for i in tl.items],
            [Status.DISETUJUI, Status.TERLAMBAT, Status.TERKUNCI, Status.BELUM_TERJADWAL],
        )
        self.assertEqual([i.terkunci for i in tl.items], [False, False, True, True])

    def test_target_hari_ini_belum_terlambat(self):
        tl = bangun_timeline([self.m(1, "100", target=HARI_INI)], HARI_INI)
        self.assertEqual(tl.items[0].status, Status.AKTIF)

    def test_tahap_aktif_tanpa_target_belum_terjadwal(self):
        item = bangun_timeline([self.m(1, "100")], HARI_INI).items[0]
        self.assertEqual(item.status, Status.BELUM_TERJADWAL)
        self.assertTrue(item.tahap_aktif)

    def test_semua_diverifikasi_tidak_ada_tahap_aktif(self):
        tl = bangun_timeline([self.m(1, "100", tingkat=100, verif=True)], HARI_INI)
        self.assertIsNone(tl.tahap_aktif_id)
        self.assertEqual(tl.items[0].status, Status.DISETUJUI)

    def test_input_acak_diurutkan_menurut_urutan(self):
        tl = bangun_timeline([self.m(2, "50"), self.m(1, "50")], HARI_INI)
        self.assertEqual([i.urutan for i in tl.items], [1, 2])


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class Dasar(TestCase):
    def setUp(self):
        self.client = APIClient()  # klien DRF: mendukung format="json" untuk PATCH/POST

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


class BuatMilestoneTests(Dasar):
    def test_dibuat_dari_template_aktif_dengan_bobot_snapshot(self):
        self.assertEqual([(m.urutan, m.bobot) for m in self.ms], [(1, Decimal("30")), (2, Decimal("30")), (3, Decimal("40"))])
        self.assertTrue(all(m.target is None and m.diverifikasi_pada is None for m in self.ms))

    def test_perubahan_template_tidak_mengubah_milestone_yang_ada(self):
        MilestoneTemplate.objects.filter(urutan=1).update(bobot=Decimal("10"))
        self.ms[0].refresh_from_db()
        self.assertEqual(self.ms[0].bobot, Decimal("30"))

    def test_dua_kali_ditolak(self):
        with self.assertRaises(ValidationError):
            buat_milestone_untuk_ta(self.ta)

    def test_template_total_bukan_100_ditolak(self):
        ta2 = TugasAkhir.objects.create(mahasiswa=self.mhs2, periode=self.periode, judul="Judul Uji Dua")
        MilestoneTemplate.objects.filter(urutan=3).update(bobot=Decimal("39"))
        with self.assertRaises(ValidationError):
            buat_milestone_untuk_ta(ta2)
        self.assertEqual(ta2.milestone.count(), 0)


class AdminIntegrasiTests(Dasar):
    def setUp(self):
        super().setUp()
        superuser = User.objects.create_superuser("TEST-SUPER-001", PASSWORD, nama_lengkap="Admin Uji Palsu")
        self.request = RequestFactory().post("/")
        self.request.user = superuser
        self.ma = TugasAkhirAdmin(TugasAkhir, site)

    def test_membuat_ta_dari_admin_membuat_milestone(self):
        ta2 = TugasAkhir(mahasiswa=self.mhs2, periode=self.periode, judul="Judul Uji Dua")
        self.ma.save_model(self.request, ta2, None, False)
        self.assertEqual(ta2.milestone.count(), 3)

    def test_mengubah_ta_tidak_membuat_milestone_baru(self):
        self.ta.judul = "Judul Uji Diubah"
        self.ma.save_model(self.request, self.ta, None, True)
        self.assertEqual(self.ta.milestone.count(), 3)

    def test_form_menolak_ta_baru_bila_template_tidak_valid(self):
        MilestoneTemplate.objects.update(aktif=False)
        form = TugasAkhirForm(
            data={"mahasiswa": self.mhs2.pk, "periode": self.periode.pk, "judul": "Judul Uji Dua", "jenis_penelitian": "", "status": "aktif"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("template milestone", " ".join(form.non_field_errors()))


class TimelineMahasiswaApiTests(Dasar):
    def test_butuh_login_dan_peran_mahasiswa(self):
        self.assertEqual(self.client.get(MHS_URL).status_code, 403)
        self.client.force_login(self.utama)
        self.assertEqual(self.client.get(MHS_URL).status_code, 403)

    def test_mahasiswa_melihat_timeline_sendiri(self):
        self.client.force_login(self.mhs)
        body = self.client.get(MHS_URL).json()
        self.assertEqual(body["tugas_akhir"]["id"], self.ta.pk)
        self.assertEqual(body["progres"], 0)
        self.assertEqual([m["urutan"] for m in body["milestone"]], [1, 2, 3])
        self.assertTrue(body["milestone"][0]["tahap_aktif"])
        self.assertEqual(body["tahap_aktif"]["id"], self.ms[0].pk)

    def test_mahasiswa_tanpa_ta_mendapat_empty_state(self):
        self.client.force_login(self.mhs2)
        body = self.client.get(MHS_URL).json()
        self.assertIsNone(body["tugas_akhir"])
        self.assertEqual(body["milestone"], [])

    def test_data_mahasiswa_lain_tidak_bocor(self):
        ta2 = TugasAkhir.objects.create(mahasiswa=self.mhs2, periode=self.periode, judul="Judul Uji Dua")
        buat_milestone_untuk_ta(ta2)
        self.client.force_login(self.mhs2)
        ids = {m["id"] for m in self.client.get(MHS_URL).json()["milestone"]}
        self.assertEqual(ids, set(ta2.milestone.values_list("id", flat=True)))
        self.assertFalse(ids & {m.pk for m in self.ms})

    def test_status_terlambat_muncul_di_tahap_aktif(self):
        Milestone.objects.filter(pk=self.ms[0].pk).update(target=timezone.localdate() - timedelta(days=2))
        self.client.force_login(self.mhs)
        statuses = [m["status"] for m in self.client.get(MHS_URL).json()["milestone"]]
        self.assertEqual(statuses, ["terlambat", "belum_terjadwal", "belum_terjadwal"])

    def test_wajib_ganti_password_diblokir(self):
        User.objects.filter(pk=self.mhs.pk).update(must_change_password=True)
        self.client.force_login(self.mhs)
        self.assertEqual(self.client.get(MHS_URL).status_code, 403)


class DosenMilestoneApiTests(Dasar):
    def setUp(self):
        super().setUp()
        self.depan = timezone.localdate() + timedelta(days=30)

    def patch_target(self, pk, target):
        return self.client.patch(url_target(pk), {"target": target}, format="json")

    def post_verif(self, pk, **data):
        return self.client.post(url_verif(pk), data, format="json")

    # --- izin ---
    def test_hanya_pembimbing_utama_ta_tersebut(self):
        for dosen in (self.pendamping, self.penguji, self.asing):
            with self.subTest(dosen=dosen.identifier):
                self.client.force_login(dosen)
                self.assertEqual(self.patch_target(self.ms[0].pk, self.depan.isoformat()).status_code, 404)
                self.assertEqual(self.post_verif(self.ms[0].pk).status_code, 404)
        self.ms[0].refresh_from_db()
        self.assertIsNone(self.ms[0].target)
        self.assertIsNone(self.ms[0].diverifikasi_pada)
        self.assertEqual(Notifikasi.objects.count(), 0)

    def test_mahasiswa_dan_anonim_ditolak(self):
        self.assertEqual(self.patch_target(self.ms[0].pk, None).status_code, 403)
        self.client.force_login(self.mhs)
        self.assertEqual(self.patch_target(self.ms[0].pk, None).status_code, 403)
        self.assertEqual(self.post_verif(self.ms[0].pk).status_code, 403)

    def test_milestone_tidak_ada(self):
        self.client.force_login(self.utama)
        self.assertEqual(self.post_verif(999999).status_code, 404)

    # --- target ---
    def test_target_ditetapkan_dengan_notifikasi_dan_audit(self):
        self.client.force_login(self.utama)
        r = self.patch_target(self.ms[0].pk, self.depan.isoformat())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["milestone"]["target"], self.depan.isoformat())
        self.assertEqual(r.json()["milestone"]["status"], "aktif")
        self.ms[0].refresh_from_db()
        self.assertEqual(self.ms[0].target, self.depan)
        notif = Notifikasi.objects.get()
        self.assertEqual((notif.user, notif.jenis), (self.mhs, "milestone_target"))
        self.assertIsNone(notif.dibaca_pada)
        log = AuditLog.objects.get(objek_tipe="milestone.Milestone")
        self.assertEqual((log.aktor, log.aksi), (self.utama, "ubah"))
        self.assertEqual(log.sebelum, {"target": None})
        self.assertEqual(log.sesudah, {"target": self.depan.isoformat()})

    def test_target_sama_tidak_mengulang_notifikasi_dan_audit(self):
        self.client.force_login(self.utama)
        self.patch_target(self.ms[0].pk, self.depan.isoformat())
        self.assertEqual(self.patch_target(self.ms[0].pk, self.depan.isoformat()).status_code, 200)
        self.assertEqual(Notifikasi.objects.count(), 1)
        self.assertEqual(AuditLog.objects.count(), 1)

    def test_target_dapat_dihapus(self):
        self.client.force_login(self.utama)
        self.patch_target(self.ms[0].pk, self.depan.isoformat())
        r = self.patch_target(self.ms[0].pk, None)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["milestone"]["status"], "belum_terjadwal")
        self.assertEqual(Notifikasi.objects.count(), 2)

    def test_target_milestone_terverifikasi_ditolak(self):
        self.client.force_login(self.utama)
        self.post_verif(self.ms[0].pk)
        self.assertEqual(self.patch_target(self.ms[0].pk, self.depan.isoformat()).status_code, 409)

    def test_target_tidak_valid(self):
        self.client.force_login(self.utama)
        self.assertEqual(self.patch_target(self.ms[0].pk, "bukan-tanggal").status_code, 400)
        self.assertEqual(self.client.patch(url_target(self.ms[0].pk), {}, format="json").status_code, 400)

    # --- verifikasi ---
    def test_verifikasi_mengubah_progres_dan_mengirim_notifikasi(self):
        self.client.force_login(self.utama)
        r = self.post_verif(self.ms[0].pk)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["milestone"]["status"], "disetujui")
        self.assertEqual(r.json()["progres"], 30)
        self.ms[0].refresh_from_db()
        self.assertEqual(self.ms[0].diverifikasi_oleh, self.utama)
        self.assertIsNotNone(self.ms[0].diverifikasi_pada)
        self.assertEqual(self.ms[0].tingkat_penyelesaian, 100)
        notif = Notifikasi.objects.get()
        self.assertEqual((notif.user, notif.jenis), (self.mhs, "milestone_diverifikasi"))
        log = AuditLog.objects.get(objek_tipe="milestone.Milestone")
        self.assertEqual(log.aktor, self.utama)
        self.assertEqual(log.sesudah["tingkat_penyelesaian"], 100)
        self.client.force_login(self.mhs)
        body = self.client.get(MHS_URL).json()
        self.assertEqual(body["progres"], 30)
        self.assertEqual(body["tahap_aktif"]["id"], self.ms[1].pk)

    def test_verifikasi_dengan_tingkat_sebagian(self):
        self.client.force_login(self.utama)
        self.assertEqual(self.post_verif(self.ms[0].pk, tingkat_penyelesaian=50).json()["progres"], 15)

    def test_tingkat_di_luar_rentang_ditolak(self):
        self.client.force_login(self.utama)
        for nilai in (101, -1):
            self.assertEqual(self.post_verif(self.ms[0].pk, tingkat_penyelesaian=nilai).status_code, 400)
        self.ms[0].refresh_from_db()
        self.assertIsNone(self.ms[0].diverifikasi_pada)

    def test_tahap_terkunci_tidak_dapat_diverifikasi(self):
        self.client.force_login(self.utama)
        self.assertEqual(self.post_verif(self.ms[1].pk).status_code, 409)
        self.ms[1].refresh_from_db()
        self.assertIsNone(self.ms[1].diverifikasi_pada)
        self.assertEqual(Notifikasi.objects.count(), 0)

    def test_verifikasi_dua_kali_ditolak(self):
        self.client.force_login(self.utama)
        self.assertEqual(self.post_verif(self.ms[0].pk).status_code, 200)
        self.assertEqual(self.post_verif(self.ms[0].pk).status_code, 409)
        self.assertEqual(Notifikasi.objects.count(), 1)

    def test_semua_tahap_diverifikasi_progres_penuh(self):
        self.client.force_login(self.utama)
        for m in self.ms:
            self.assertEqual(self.post_verif(m.pk).status_code, 200)
        self.client.force_login(self.mhs)
        body = self.client.get(MHS_URL).json()
        self.assertEqual(body["progres"], 100)
        self.assertIsNone(body["tahap_aktif"])