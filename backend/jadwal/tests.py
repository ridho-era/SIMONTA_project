from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Role, User
from akademik.models import Penugasan, PeriodeAkademik, TugasAkhir
from notifikasi.models import Notifikasi

from .models import Bimbingan

PASSWORD = "Sandi-Uji-12345!"
URL_MHS = "/api/v1/mahasiswa/jadwal/"
URL_DSN_INBOX = "/api/v1/dosen/jadwal/permohonan/"
URL_DASHBOARD_MHS = "/api/v1/mahasiswa/dashboard/"
URL_DASHBOARD_DSN = "/api/v1/dosen/dashboard/"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class JadwalApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.mahasiswa = User.objects.create_user(
            "T-JAD-MHS-01", PASSWORD, role=Role.MAHASISWA, nama_lengkap="Mahasiswa Jadwal Uji"
        )
        self.mahasiswa_lain = User.objects.create_user(
            "T-JAD-MHS-02", PASSWORD, role=Role.MAHASISWA, nama_lengkap="Mahasiswa Lain Uji"
        )
        self.dosen = User.objects.create_user(
            "T-JAD-DSN-01", PASSWORD, role=Role.DOSEN, nama_lengkap="Dosen Jadwal Uji"
        )
        self.dosen_kedua = User.objects.create_user(
            "T-JAD-DSN-02", PASSWORD, role=Role.DOSEN, nama_lengkap="Dosen Kedua Uji"
        )
        self.dosen_asing = User.objects.create_user(
            "T-JAD-DSN-03", PASSWORD, role=Role.DOSEN, nama_lengkap="Dosen Asing Uji"
        )
        self.periode = PeriodeAkademik.objects.create(
            label="Periode Jadwal Uji",
            tanggal_mulai=timezone.localdate() - timedelta(days=30),
            tanggal_selesai=timezone.localdate() + timedelta(days=300),
        )
        self.ta = self.buat_ta(self.mahasiswa, self.dosen, "Judul TA Jadwal Uji")
        self.ta_lain = self.buat_ta(self.mahasiswa_lain, self.dosen, "Judul TA Mahasiswa Lain")
        Penugasan.objects.create(tugas_akhir=self.ta, dosen=self.dosen_kedua, peran=Penugasan.Peran.PENDAMPING)

    def buat_ta(self, mahasiswa, dosen, judul):
        ta = TugasAkhir.objects.create(mahasiswa=mahasiswa, periode=self.periode, judul=judul)
        Penugasan.objects.create(tugas_akhir=ta, dosen=dosen, peran=Penugasan.Peran.UTAMA)
        return ta

    def rentang(self, hari=2, jam=10, durasi=60):
        start = timezone.localtime(timezone.now()).replace(hour=jam, minute=0, second=0, microsecond=0) + timedelta(days=hari)
        # Pastikan tanggal mulai selalu di masa depan walau pengujian dijalankan malam hari.
        if start <= timezone.localtime(timezone.now()):
            start += timedelta(days=1)
        return start, start + timedelta(minutes=durasi)

    def payload(self, dosen_id=None, mulai=None, selesai=None, mode="luring", lokasi="", agenda="Diskusi metodologi"):
        mulai, selesai = (mulai, selesai) if mulai and selesai else self.rentang()
        return {
            "dosen_id": dosen_id or self.dosen.pk,
            "mulai": mulai.isoformat(),
            "selesai": selesai.isoformat(),
            "mode": mode,
            "lokasi_atau_tautan": lokasi,
            "agenda": agenda,
        }

    def ajukan(self, mahasiswa=None, payload=None):
        self.client.force_login(mahasiswa or self.mahasiswa)
        return self.client.post(URL_MHS, payload or self.payload(), format="json")

    def setujui(self, item_id, dosen=None, lokasi="Ruang konsultasi uji"):
        self.client.force_login(dosen or self.dosen)
        return self.client.post(
            f"/api/v1/dosen/jadwal/{item_id}/setujui/",
            {"lokasi_atau_tautan": lokasi},
            format="json",
        )

    def test_mahasiswa_dapat_mengajukan_ke_dosen_yang_ditugaskan(self):
        response = self.ajukan()
        self.assertEqual(response.status_code, 201)
        item = Bimbingan.objects.get(pk=response.json()["id"])
        self.assertEqual(item.status, Bimbingan.Status.MENUNGGU_KONFIRMASI)
        self.assertEqual(item.tugas_akhir_id, self.ta.pk)
        self.assertTrue(Notifikasi.objects.filter(user=self.dosen, jenis=Notifikasi.Jenis.PERMOHONAN_JADWAL).exists())

    def test_mahasiswa_hanya_boleh_memilih_dosen_dalam_penugasan(self):
        response = self.ajukan(payload=self.payload(dosen_id=self.dosen_asing.pk))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Bimbingan.objects.count(), 0)

    def test_mahasiswa_hanya_melihat_jadwal_tugas_akhir_sendiri(self):
        pertama = self.ajukan().json()
        rentang = self.rentang(hari=4)
        kedua = self.ajukan(self.mahasiswa_lain, self.payload(mulai=rentang[0], selesai=rentang[1])).json()
        self.client.force_login(self.mahasiswa)
        body = self.client.get(URL_MHS).json()
        self.assertEqual([x["id"] for x in body["mendatang"]], [pertama["id"]])
        self.assertNotIn(kedua["id"], [x["id"] for x in body["mendatang"]])

    def test_validasi_waktu_masa_lalu_dan_selesai_sebelum_mulai(self):
        now = timezone.now()
        past = self.payload(mulai=now - timedelta(days=1), selesai=now - timedelta(days=1) + timedelta(minutes=30))
        self.assertEqual(self.ajukan(payload=past).status_code, 400)
        start, end = self.rentang()
        salah = self.payload(mulai=start, selesai=start)
        self.assertEqual(self.ajukan(payload=salah).status_code, 400)
        self.assertEqual(Bimbingan.objects.count(), 0)

    def test_endpoint_mahasiswa_dan_dosen_membutuhkan_role_yang_benar(self):
        self.client.force_login(self.dosen)
        self.assertEqual(self.client.get(URL_MHS).status_code, 403)
        self.client.force_login(self.mahasiswa)
        self.assertEqual(self.client.get(URL_DSN_INBOX).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(URL_MHS).status_code, 403)

    def test_dosen_hanya_melihat_permohonan_yang_dituju_kepadanya(self):
        one = self.ajukan().json()
        start, end = self.rentang(hari=3)
        self.ajukan(payload=self.payload(dosen_id=self.dosen_kedua.pk, mulai=start, selesai=end))
        self.client.force_login(self.dosen)
        body = self.client.get(URL_DSN_INBOX).json()
        self.assertEqual(body["jumlah"], 1)
        self.assertEqual(body["hasil"][0]["id"], one["id"])

    def test_dosen_lain_tidak_dapat_melakukan_aksi_pada_permohonan(self):
        item = self.ajukan().json()
        response = self.setujui(item["id"], dosen=self.dosen_asing)
        self.assertEqual(response.status_code, 404)

    def test_persetujuan_wajib_mengisi_lokasi_atau_tautan(self):
        item = self.ajukan().json()
        response = self.setujui(item["id"], lokasi="")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Bimbingan.objects.get(pk=item["id"]).status, Bimbingan.Status.MENUNGGU_KONFIRMASI)

    def test_mode_daring_memerlukan_url_valid_saat_disetujui(self):
        payload = self.payload(mode="daring")
        item = self.ajukan(payload=payload).json()
        response = self.setujui(item["id"], lokasi="bukan-url")
        self.assertEqual(response.status_code, 409)
        response = self.setujui(item["id"], lokasi="https://meet.google.com/abc-defg-hij")
        self.assertEqual(response.status_code, 200)

    def test_jadwal_beririsan_ditolak_untuk_dosen_yang_sama(self):
        start, end = self.rentang()
        first = self.ajukan(payload=self.payload(mulai=start, selesai=end)).json()
        self.assertEqual(self.setujui(first["id"]).status_code, 200)
        # Permohonan dari mahasiswa lain ke dosen yang sama pada rentang beririsan.
        overlap_start = start + timedelta(minutes=30)
        overlap_end = end + timedelta(minutes=30)
        second = self.ajukan(
            mahasiswa=self.mahasiswa_lain,
            payload=self.payload(mulai=overlap_start, selesai=overlap_end),
        ).json()
        response = self.setujui(second["id"])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Bimbingan.objects.get(pk=second["id"]).status, Bimbingan.Status.MENUNGGU_KONFIRMASI)

    def test_jadwal_berdempetan_tanpa_overlap_dapat_disetujui(self):
        start, end = self.rentang()
        first = self.ajukan(payload=self.payload(mulai=start, selesai=end)).json()
        self.assertEqual(self.setujui(first["id"]).status_code, 200)
        second = self.ajukan(
            mahasiswa=self.mahasiswa_lain,
            payload=self.payload(mulai=end, selesai=end + timedelta(minutes=45)),
        ).json()
        self.assertEqual(self.setujui(second["id"]).status_code, 200)

    def test_waktu_bersamaan_dapat_disetujui_untuk_dosen_yang_berbeda(self):
        start, end = self.rentang()
        first = self.ajukan(payload=self.payload(mulai=start, selesai=end)).json()
        self.assertEqual(self.setujui(first["id"]).status_code, 200)
        self.client.force_login(self.mahasiswa)
        second_response = self.client.post(
            URL_MHS,
            self.payload(dosen_id=self.dosen_kedua.pk, mulai=start, selesai=end),
            format="json",
        )
        self.assertEqual(second_response.status_code, 201)
        second_id = second_response.json()["id"]
        self.client.force_login(self.dosen_kedua)
        response = self.client.post(
            f"/api/v1/dosen/jadwal/{second_id}/setujui/",
            {"lokasi_atau_tautan": "Ruang konsultasi kedua"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_penolakan_memerlukan_alasan_dan_memberi_notifikasi(self):
        item = self.ajukan().json()
        self.client.force_login(self.dosen)
        base = f"/api/v1/dosen/jadwal/{item['id']}/tolak/"
        self.assertEqual(self.client.post(base, {"alasan": "  "}, format="json").status_code, 400)
        response = self.client.post(base, {"alasan": "Mohon pilih waktu konsultasi lain."}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Bimbingan.objects.get(pk=item["id"]).status, Bimbingan.Status.DITOLAK)
        self.assertTrue(Notifikasi.objects.filter(user=self.mahasiswa, jenis=Notifikasi.Jenis.JADWAL_DITOLAK).exists())

    def test_dosen_dapat_mengusulkan_waktu_lain_dan_mahasiswa_diberi_notifikasi(self):
        item = self.ajukan().json()
        start, end = self.rentang(hari=5, jam=13)
        self.client.force_login(self.dosen)
        response = self.client.post(
            f"/api/v1/dosen/jadwal/{item['id']}/usulkan/",
            {"mulai": start.isoformat(), "selesai": end.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        updated = Bimbingan.objects.get(pk=item["id"])
        self.assertEqual(updated.status, Bimbingan.Status.MENUNGGU_KONFIRMASI)
        self.assertEqual(updated.mulai, start)
        self.assertTrue(Notifikasi.objects.filter(user=self.mahasiswa, jenis=Notifikasi.Jenis.JADWAL_DIUSULKAN).exists())

    def test_reschedule_menautkan_permohonan_lama_dan_membatalkan_lama_setelah_diterima(self):
        old_start, old_end = self.rentang(hari=3)
        old = self.ajukan(payload=self.payload(mulai=old_start, selesai=old_end)).json()
        self.assertEqual(self.setujui(old["id"]).status_code, 200)

        new_start, new_end = self.rentang(hari=6, jam=14)
        self.client.force_login(self.mahasiswa)
        response = self.client.post(
            f"{URL_MHS}{old['id']}/reschedule/",
            {
                "mulai": new_start.isoformat(),
                "selesai": new_end.isoformat(),
                "mode": "daring",
                "lokasi_atau_tautan": "",
                "agenda": "Diskusi hasil penelitian",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        new_id = response.json()["id"]
        self.assertEqual(response.json()["menggantikan"], old["id"])
        self.assertEqual(Bimbingan.objects.get(pk=old["id"]).status, Bimbingan.Status.DISETUJUI)

        self.assertEqual(self.setujui(new_id, lokasi="https://meet.google.com/klm-nopq-rst").status_code, 200)
        self.assertEqual(Bimbingan.objects.get(pk=old["id"]).status, Bimbingan.Status.DIBATALKAN)
        self.assertEqual(Bimbingan.objects.get(pk=new_id).status, Bimbingan.Status.DISETUJUI)

    def test_reschedule_jadwal_pending_membatalkan_permohonan_lama(self):
        old = self.ajukan().json()
        start, end = self.rentang(hari=5)
        self.client.force_login(self.mahasiswa)
        response = self.client.post(
            f"{URL_MHS}{old['id']}/reschedule/",
            {"mulai": start.isoformat(), "selesai": end.isoformat(), "mode": "luring"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Bimbingan.objects.get(pk=old["id"]).status, Bimbingan.Status.DIBATALKAN)
        self.assertEqual(Bimbingan.objects.get(pk=response.json()["id"]).menggantikan_id, old["id"])

    def test_dashboard_mahasiswa_memuat_bimbingan_terdekat(self):
        item = self.ajukan().json()
        self.client.force_login(self.mahasiswa)
        body = self.client.get(URL_DASHBOARD_MHS).json()
        self.assertEqual(body["bimbingan_terdekat"]["id"], item["id"])
        self.assertEqual(body["bimbingan_terdekat"]["status"], Bimbingan.Status.MENUNGGU_KONFIRMASI)

    def test_dashboard_dosen_memuat_permohonan_yang_ditujukan(self):
        item = self.ajukan().json()
        self.client.force_login(self.dosen)
        body = self.client.get(URL_DASHBOARD_DSN).json()
        self.assertEqual(body["permohonan_jadwal"]["jumlah"], 1)
        self.assertEqual(body["permohonan_jadwal"]["hasil"][0]["id"], item["id"])
        self.client.force_login(self.dosen_asing)
        body = self.client.get(URL_DASHBOARD_DSN).json()
        self.assertEqual(body["permohonan_jadwal"]["jumlah"], 0)
