from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.forms.models import inlineformset_factory
from django.test import TestCase, override_settings

from accounts.models import Role, User

from .admin import PenugasanInlineFormSet
from .models import (
    JenisSanksi,
    KonfigurasiDenda,
    MilestoneTemplate,
    Penugasan,
    PeriodeAkademik,
    TugasAkhir,
)

FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
PASSWORD = "Sandi-Uji-12345!"  # semua data di tes ini sintetis dan jelas palsu


def buat_user(identifier, role, nama):
    return User.objects.create_user(identifier, PASSWORD, role=role, nama_lengkap=nama)


def buat_periode(label="Periode Uji A", aktif=False):
    periode = PeriodeAkademik(
        label=label,
        tanggal_mulai=date(2030, 1, 1),
        tanggal_selesai=date(2030, 6, 30),
        aktif=aktif,
    )
    periode.save()
    return periode


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class AkademikBase(TestCase):
    def setUp(self):
        self.mhs = buat_user("TEST-MHS-001", Role.MAHASISWA, "Mahasiswa Uji Palsu")
        self.mhs2 = buat_user("TEST-MHS-002", Role.MAHASISWA, "Mahasiswa Uji Palsu Dua")
        self.dosen1 = buat_user("TEST-DSN-001", Role.DOSEN, "Dosen Uji Palsu Satu")
        self.dosen2 = buat_user("TEST-DSN-002", Role.DOSEN, "Dosen Uji Palsu Dua")
        self.dosen3 = buat_user("TEST-DSN-003", Role.DOSEN, "Dosen Uji Palsu Tiga")
        self.periode = buat_periode()

    def buat_ta(self, mahasiswa=None, **kw):
        return TugasAkhir.objects.create(
            mahasiswa=mahasiswa or self.mhs,
            periode=self.periode,
            judul=kw.pop("judul", "Judul Uji Palsu"),
            **kw,
        )


class PeriodeTests(AkademikBase):
    def test_dua_periode_aktif_ditolak_oleh_clean(self):
        buat_periode("Periode Uji Aktif", aktif=True)
        kedua = PeriodeAkademik(
            label="Periode Uji Lain",
            tanggal_mulai=date(2031, 1, 1),
            tanggal_selesai=date(2031, 6, 30),
            aktif=True,
        )
        with self.assertRaises(ValidationError):
            kedua.full_clean()

    def test_dua_periode_aktif_ditolak_oleh_database(self):
        buat_periode("Periode Uji Aktif", aktif=True)
        kedua = PeriodeAkademik(
            label="Periode Uji Lain",
            tanggal_mulai=date(2031, 1, 1),
            tanggal_selesai=date(2031, 6, 30),
            aktif=True,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            kedua.save()

    def test_banyak_periode_nonaktif_boleh(self):
        buat_periode("Periode Uji B")
        buat_periode("Periode Uji C")
        self.assertEqual(PeriodeAkademik.objects.filter(aktif=False).count(), 3)

    def test_mengganti_periode_aktif_setelah_menonaktifkan(self):
        lama = buat_periode("Periode Uji Aktif", aktif=True)
        lama.aktif = False
        lama.save()
        baru = buat_periode("Periode Uji Baru", aktif=True)
        self.assertEqual(PeriodeAkademik.aktif_sekarang(), baru)

    def test_tanggal_selesai_sebelum_mulai_ditolak(self):
        periode = PeriodeAkademik(
            label="Periode Uji Salah",
            tanggal_mulai=date(2030, 6, 30),
            tanggal_selesai=date(2030, 1, 1),
        )
        with self.assertRaises(ValidationError):
            periode.full_clean()


class TugasAkhirTests(AkademikBase):
    def test_satu_ta_aktif_per_mahasiswa_oleh_clean(self):
        self.buat_ta()
        kedua = TugasAkhir(mahasiswa=self.mhs, periode=self.periode, judul="Judul Uji Dua")
        with self.assertRaises(ValidationError):
            kedua.full_clean()

    def test_satu_ta_aktif_per_mahasiswa_oleh_database(self):
        self.buat_ta()
        kedua = TugasAkhir(mahasiswa=self.mhs, periode=self.periode, judul="Judul Uji Dua")
        with self.assertRaises(IntegrityError), transaction.atomic():
            kedua.save()

    def test_ta_baru_boleh_setelah_yang_lama_selesai(self):
        lama = self.buat_ta()
        lama.status = TugasAkhir.Status.SELESAI
        lama.save()
        self.assertIsNone(lama.slot_aktif)
        baru = self.buat_ta(judul="Judul Uji Baru")
        self.assertTrue(baru.slot_aktif)

    def test_mahasiswa_berbeda_masing_masing_punya_ta_aktif(self):
        self.buat_ta(self.mhs)
        self.buat_ta(self.mhs2)
        self.assertEqual(TugasAkhir.objects.filter(status="aktif").count(), 2)

    def test_hanya_akun_mahasiswa_yang_boleh_punya_ta(self):
        ta = TugasAkhir(mahasiswa=self.dosen1, periode=self.periode, judul="Judul Uji")
        with self.assertRaises(ValidationError):
            ta.full_clean()


class PenugasanTests(AkademikBase):
    def setUp(self):
        super().setUp()
        self.ta = self.buat_ta()

    def tugaskan(self, dosen, peran):
        return Penugasan.objects.create(tugas_akhir=self.ta, dosen=dosen, peran=peran)

    def test_satu_pembimbing_utama_per_ta(self):
        self.tugaskan(self.dosen1, "utama")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.tugaskan(self.dosen2, "utama")

    def test_pendamping_dan_penguji_boleh_banyak(self):
        self.tugaskan(self.dosen1, "utama")
        self.tugaskan(self.dosen2, "pendamping")
        self.tugaskan(self.dosen3, "penguji")
        self.assertEqual(self.ta.penugasan.count(), 3)

    def test_dosen_sama_tidak_boleh_dua_kali_pada_ta_yang_sama(self):
        self.tugaskan(self.dosen1, "utama")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.tugaskan(self.dosen1, "penguji")

    def test_dosen_boleh_membimbing_banyak_ta(self):
        ta2 = self.buat_ta(self.mhs2)
        self.tugaskan(self.dosen1, "utama")
        Penugasan.objects.create(tugas_akhir=ta2, dosen=self.dosen1, peran="utama")
        self.assertEqual(self.dosen1.penugasan_dosen.count(), 2)

    def test_hanya_akun_dosen_yang_boleh_ditugaskan(self):
        penugasan = Penugasan(tugas_akhir=self.ta, dosen=self.mhs, peran="pendamping")
        with self.assertRaises(ValidationError):
            penugasan.full_clean()

    def test_mengubah_peran_membebaskan_slot_utama(self):
        utama = self.tugaskan(self.dosen1, "utama")
        utama.peran = "pendamping"
        utama.save()
        self.assertIsNone(utama.slot_utama)
        self.tugaskan(self.dosen2, "utama")  # kini boleh
        self.assertEqual(self.ta.penugasan.filter(peran="utama").count(), 1)


class PenugasanFormSetTests(AkademikBase):
    def setUp(self):
        super().setUp()
        self.ta = self.buat_ta()
        self.FormSet = inlineformset_factory(
            TugasAkhir,
            Penugasan,
            formset=PenugasanInlineFormSet,
            fields=("dosen", "peran"),
            extra=0,
        )

    def data(self, baris):
        data = {
            "penugasan-TOTAL_FORMS": str(len(baris)),
            "penugasan-INITIAL_FORMS": "0",
            "penugasan-MIN_NUM_FORMS": "0",
            "penugasan-MAX_NUM_FORMS": "1000",
        }
        for i, (dosen, peran) in enumerate(baris):
            data[f"penugasan-{i}-dosen"] = str(dosen.pk)
            data[f"penugasan-{i}-peran"] = peran
        return data

    def test_dua_pembimbing_utama_dalam_satu_form_ditolak(self):
        formset = self.FormSet(
            data=self.data([(self.dosen1, "utama"), (self.dosen2, "utama")]),
            instance=self.ta,
        )
        self.assertFalse(formset.is_valid())
        self.assertIn("satu pembimbing utama", " ".join(formset.non_form_errors()))

    def test_dosen_ganda_dalam_satu_form_ditolak(self):
        formset = self.FormSet(
            data=self.data([(self.dosen1, "utama"), (self.dosen1, "penguji")]),
            instance=self.ta,
        )
        self.assertFalse(formset.is_valid())

    def test_susunan_valid_diterima(self):
        formset = self.FormSet(
            data=self.data(
                [(self.dosen1, "utama"), (self.dosen2, "pendamping"), (self.dosen3, "penguji")]
            ),
            instance=self.ta,
        )
        self.assertTrue(formset.is_valid(), formset.errors)


class MilestoneTemplateTests(TestCase):
    def buat(self, urutan, bobot, aktif=True):
        return MilestoneTemplate.objects.create(
            urutan=urutan, nama=f"Tahap Uji {urutan}", bobot=Decimal(bobot), aktif=aktif
        )

    def test_total_bobot_hanya_menghitung_template_aktif(self):
        self.buat(1, "60")
        self.buat(2, "25.50")
        self.buat(3, "30", aktif=False)
        self.assertEqual(MilestoneTemplate.total_bobot_aktif(), Decimal("85.50"))

    def test_total_melebihi_100_ditolak(self):
        self.buat(1, "60")
        self.buat(2, "40")
        tambahan = MilestoneTemplate(urutan=3, nama="Tahap Uji 3", bobot=Decimal("10"), aktif=True)
        with self.assertRaises(ValidationError) as ctx:
            tambahan.full_clean()
        self.assertIn("bobot", ctx.exception.message_dict)

    def test_template_nonaktif_boleh_melebihi_total(self):
        self.buat(1, "100")
        cadangan = MilestoneTemplate(
            urutan=2, nama="Tahap Cadangan", bobot=Decimal("50"), aktif=False
        )
        cadangan.full_clean()  # tidak melempar

    def test_mengubah_bobot_baris_sendiri_tidak_dihitung_dua_kali(self):
        satu = self.buat(1, "60")
        self.buat(2, "40")
        satu.bobot = Decimal("60")
        satu.full_clean()  # total tetap 100, valid

    def test_pastikan_total_valid(self):
        with self.assertRaises(ValidationError):  # belum ada template
            MilestoneTemplate.pastikan_total_valid()
        self.buat(1, "60")
        self.buat(2, "39.50")
        with self.assertRaises(ValidationError):  # 99.50
            MilestoneTemplate.pastikan_total_valid()
        self.buat(3, "0.50")
        MilestoneTemplate.pastikan_total_valid()  # tepat 100

    def test_bobot_nol_atau_negatif_ditolak(self):
        for nilai in ("0", "-5"):
            with self.subTest(bobot=nilai):
                template = MilestoneTemplate(urutan=1, nama="Tahap Uji", bobot=Decimal(nilai))
                with self.assertRaises(ValidationError):
                    template.full_clean()

    def test_urutan_unik(self):
        self.buat(1, "50")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.buat(1, "50")


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class KonfigurasiDendaTests(TestCase):
    def test_label_simulasi_default_aktif(self):
        periode = buat_periode()
        konfigurasi = KonfigurasiDenda.objects.create(
            periode=periode, jenis="telat_revisi", tarif=1, batas_per_catatan=2
        )
        self.assertTrue(konfigurasi.label_simulasi)
        self.assertEqual(konfigurasi.toleransi_hari, 0)

    def test_satu_konfigurasi_per_periode_dan_jenis(self):
        periode = buat_periode()
        KonfigurasiDenda.objects.create(
            periode=periode, jenis="telat_revisi", tarif=1, batas_per_catatan=2
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            KonfigurasiDenda.objects.create(
                periode=periode, jenis="telat_revisi", tarif=3, batas_per_catatan=4
            )
        KonfigurasiDenda.objects.create(
            periode=periode, jenis="telat_berkas", tarif=3, batas_per_catatan=4
        )
        self.assertEqual(KonfigurasiDenda.objects.count(), 2)

    def test_jenis_yang_sama_boleh_di_periode_lain(self):
        a, b = buat_periode("Periode Uji A"), buat_periode("Periode Uji B")
        for periode in (a, b):
            KonfigurasiDenda.objects.create(
                periode=periode, jenis="telat_revisi", tarif=1, batas_per_catatan=2
            )
        self.assertEqual(KonfigurasiDenda.objects.count(), 2)


class JenisSanksiTests(TestCase):
    def test_nama_unik(self):
        JenisSanksi.objects.create(nama="Sanksi Uji A")
        with self.assertRaises(IntegrityError), transaction.atomic():
            JenisSanksi.objects.create(nama="Sanksi Uji A")