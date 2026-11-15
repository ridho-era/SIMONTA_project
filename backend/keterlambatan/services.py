"""Perhitungan dan alur bisnis keterlambatan sesuai BR-05."""
import hashlib

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import Role
from akademik.models import KonfigurasiDenda, Penugasan, TugasAkhir
from audit.models import AuditLog
from audit.services import catat_audit, snapshot
from dokumen.models import DokumenVersi
from notifikasi.models import Notifikasi
from notifikasi.services import notify
from review.models import Review

from .models import CatatanKeterlambatan, Keberatan, SanksiTercatat

STATUS_TERBUKA = (
    CatatanKeterlambatan.StatusPenilaian.USULAN,
    CatatanKeterlambatan.StatusPenilaian.KEBERATAN_DITINJAU,
)


def _format_rupiah(nilai):
    """Memformat angka rupiah dengan titik sebagai pemisah ribuan."""
    return f"{int(nilai):,}".replace(",", ".")


def hitung_denda(*, tenggat, realisasi=None, tarif, toleransi, batas, hari_ini=None):
    """Menghitung denda dalam hari kalender; realisasi kosong memakai tanggal hari ini."""
    tanggal_hitung = realisasi or hari_ini or timezone.localdate()
    hari_terlambat = max((tanggal_hitung - tenggat).days, 0)
    hari_dikenai = max(hari_terlambat - int(toleransi), 0)
    subtotal = hari_dikenai * int(tarif)
    nominal = min(subtotal, int(batas))
    return {
        "tanggal_hitung": tanggal_hitung,
        "hari_terlambat": hari_terlambat,
        "hari_dikenai": hari_dikenai,
        "tarif": int(tarif),
        "toleransi_hari": int(toleransi),
        "batas_per_catatan": int(batas),
        "subtotal": subtotal,
        "nominal": nominal,
        "rumus": (
            f"min(max({hari_terlambat} - {int(toleransi)}, 0) "
            f"× Rp{_format_rupiah(tarif)}, Rp{_format_rupiah(batas)})"
        ),
    }


def konfigurasi_untuk(tugas_akhir, jenis):
    """Konfigurasi harus berasal dari periode yang melekat pada tugas akhir."""
    return KonfigurasiDenda.objects.filter(
        periode_id=tugas_akhir.periode_id,
        jenis=jenis,
    ).select_related("periode").first()


def _nilai_snapshot(konfigurasi):
    return {
        "tarif": konfigurasi.tarif,
        "toleransi_hari": konfigurasi.toleransi_hari,
        "batas_per_catatan": konfigurasi.batas_per_catatan,
        "label_simulasi": konfigurasi.label_simulasi,
    }


def _hitung_dari_catatan(catatan, *, hari_ini=None):
    return hitung_denda(
        tenggat=catatan.tenggat,
        realisasi=catatan.realisasi,
        tarif=catatan.tarif,
        toleransi=catatan.toleransi_hari,
        batas=catatan.batas_per_catatan,
        hari_ini=hari_ini,
    )


def realisasi_revisi(review):
    """Tanggal unggahan versi pertama setelah versi yang mendapat review revisi."""
    versi = (
        DokumenVersi.objects.filter(
            dokumen_id=review.versi.dokumen_id,
            nomor_versi__gt=review.versi.nomor_versi,
        )
        .order_by("diunggah_pada", "nomor_versi", "id")
        .first()
    )
    if versi is None:
        return None
    return timezone.localtime(versi.diunggah_pada).date()


def _review_dari_pembimbing(review):
    """Review dari pembimbing utama atau pendamping dapat memiliki tenggat revisi."""
    return Penugasan.objects.filter(
        tugas_akhir_id=review.versi.dokumen.milestone.tugas_akhir_id,
        dosen_id=review.pemberi_id,
        peran__in=(Penugasan.Peran.UTAMA, Penugasan.Peran.PENDAMPING),
    ).exists()


def _simpan_perhitungan(catatan, *, hari_ini=None):
    hasil = _hitung_dari_catatan(catatan, hari_ini=hari_ini)
    catatan.hari_terlambat = hasil["hari_terlambat"]
    catatan.hari_dikenai = hasil["hari_dikenai"]
    catatan.nominal = hasil["nominal"]
    return hasil


def proses_satu_review(review, *, hari_ini=None):
    """Membuat atau memperbarui usulan denda untuk satu review revisi yang terlewat."""
    hari_ini = hari_ini or timezone.localdate()
    if (
        review.status != Review.Status.TERBIT
        or review.rekomendasi != Review.Rekomendasi.PERLU_REVISI
        or review.tenggat_revisi is None
        or review.tenggat_revisi >= hari_ini
    ):
        return None

    milestone = review.versi.dokumen.milestone
    tugas_akhir = milestone.tugas_akhir
    if tugas_akhir.status != TugasAkhir.Status.AKTIF or not _review_dari_pembimbing(review):
        return None

    konfigurasi = konfigurasi_untuk(tugas_akhir, KonfigurasiDenda.Jenis.TELAT_REVISI)
    if konfigurasi is None:
        return None

    tanggal_realisasi = realisasi_revisi(review)
    # Jika versi revisi sudah dikumpulkan sebelum atau tepat pada tenggat, tidak ada denda.
    if tanggal_realisasi is not None and tanggal_realisasi <= review.tenggat_revisi:
        return None

    sumber_kunci = f"review:{review.pk}"
    with transaction.atomic():
        catatan = (
            CatatanKeterlambatan.objects.select_for_update()
            .filter(sumber_kunci=sumber_kunci)
            .first()
        )
        defaults = {
            "tugas_akhir": tugas_akhir,
            "konfigurasi": konfigurasi,
            "jenis": KonfigurasiDenda.Jenis.TELAT_REVISI,
            "review": review,
            "milestone": milestone,
            "nama_dokumen": review.versi.nama_asli,
            "tenggat": review.tenggat_revisi,
            "realisasi": tanggal_realisasi,
            **_nilai_snapshot(konfigurasi),
            "status_penilaian": CatatanKeterlambatan.StatusPenilaian.USULAN,
            "sumber_kunci": sumber_kunci,
        }
        if catatan is None:
            catatan = CatatanKeterlambatan(**defaults)
            _simpan_perhitungan(catatan, hari_ini=hari_ini)
            catatan.save()
            catat_audit(
                None,
                AuditLog.Aksi.TAMBAH,
                catatan,
                sesudah=snapshot(catatan),
                keterangan="Catatan keterlambatan revisi dibuat otomatis.",
            )
            return catatan

        if catatan.status_penilaian in {
            CatatanKeterlambatan.StatusPenilaian.DITETAPKAN,
            CatatanKeterlambatan.StatusPenilaian.DIBATALKAN,
        }:
            return catatan

        sebelum = snapshot(catatan)
        for field, value in defaults.items():
            if field != "status_penilaian":
                setattr(catatan, field, value)
        _simpan_perhitungan(catatan, hari_ini=hari_ini)
        catatan.save()
        catat_audit(
            None,
            AuditLog.Aksi.UBAH,
            catatan,
            sebelum=sebelum,
            sesudah=snapshot(catatan),
            keterangan="Perhitungan keterlambatan disinkronkan dengan tenggat/realisasi terbaru.",
        )
        return catatan


def proses_keterlambatan_harian(*, hari_ini=None):
    """Pemroses harian idempoten untuk seluruh review revisi yang sudah melewati tenggat."""
    hari_ini = hari_ini or timezone.localdate()
    reviews = (
        Review.objects.filter(
            status=Review.Status.TERBIT,
            rekomendasi=Review.Rekomendasi.PERLU_REVISI,
            tenggat_revisi__lt=hari_ini,
            versi__dokumen__milestone__tugas_akhir__status=TugasAkhir.Status.AKTIF,
        )
        .select_related(
            "pemberi",
            "versi__dokumen__milestone__tugas_akhir__periode",
        )
        .order_by("tenggat_revisi", "id")
    )
    jumlah_dibuat = 0
    jumlah_diperbarui = 0
    for review in reviews.iterator(chunk_size=200):
        ada = CatatanKeterlambatan.objects.filter(sumber_kunci=f"review:{review.pk}").exists()
        catatan = proses_satu_review(review, hari_ini=hari_ini)
        if catatan is not None:
            if ada:
                jumlah_diperbarui += 1
            else:
                jumlah_dibuat += 1
    return {"diperiksa": reviews.count(), "dibuat": jumlah_dibuat, "diperbarui": jumlah_diperbarui}


def buat_catatan_administrasi(
    *, tugas_akhir, nama_dokumen, tenggat, realisasi=None, aktor=None
):
    """Membuat catatan manual keterlambatan berkas administrasi."""
    nama_dokumen = (nama_dokumen or "").strip()
    if not nama_dokumen:
        raise ValidationError({"nama_dokumen": "Nama berkas administrasi wajib diisi."})
    tanggal_hitung = realisasi or timezone.localdate()
    if tanggal_hitung > timezone.localdate():
        raise ValidationError({"realisasi": "Tanggal realisasi tidak boleh berada di masa depan."})
    if tanggal_hitung <= tenggat:
        raise ValidationError({"realisasi": "Tanggal realisasi harus setelah tenggat agar tercatat terlambat."})

    konfigurasi = konfigurasi_untuk(tugas_akhir, KonfigurasiDenda.Jenis.TELAT_BERKAS)
    if konfigurasi is None:
        raise ValidationError("Konfigurasi denda berkas administrasi untuk periode ini belum tersedia.")

    ringkas = f"{tugas_akhir.pk}|{nama_dokumen.casefold()}|{tenggat.isoformat()}"
    sumber_kunci = "berkas:" + hashlib.sha256(ringkas.encode("utf-8")).hexdigest()
    with transaction.atomic():
        existing = CatatanKeterlambatan.objects.select_for_update().filter(sumber_kunci=sumber_kunci).first()
        if existing:
            raise ValidationError("Catatan untuk berkas dan tenggat tersebut sudah pernah dibuat.")
        catatan = CatatanKeterlambatan(
            tugas_akhir=tugas_akhir,
            konfigurasi=konfigurasi,
            jenis=KonfigurasiDenda.Jenis.TELAT_BERKAS,
            nama_dokumen=nama_dokumen,
            tenggat=tenggat,
            realisasi=realisasi,
            dibuat_oleh=aktor,
            sumber_kunci=sumber_kunci,
            **_nilai_snapshot(konfigurasi),
        )
        _simpan_perhitungan(catatan)
        catatan.save()
        catat_audit(
            aktor,
            AuditLog.Aksi.TAMBAH,
            catatan,
            sesudah=snapshot(catatan),
            keterangan="Catatan keterlambatan berkas administrasi dibuat manual.",
        )
        return catatan


def _penugasan_utama(tugas_akhir, dosen):
    return Penugasan.objects.filter(
        tugas_akhir=tugas_akhir,
        dosen=dosen,
        peran=Penugasan.Peran.UTAMA,
    ).exists()


def simpan_atau_ajukan_keberatan(
    *,
    catatan,
    mahasiswa,
    alasan,
    bukti=None,
    nama_bukti="",
    ukuran_bukti=None,
    aksi,
):
    """Satu baris keberatan per catatan; kirim ulang hanya setelah diminta melengkapi."""
    alasan = (alasan or "").strip()
    if not alasan:
        raise ValidationError({"alasan": "Alasan keberatan wajib diisi."})
    if aksi not in {"simpan_draf", "ajukan"}:
        raise ValidationError({"aksi": "Aksi harus simpan_draf atau ajukan."})

    with transaction.atomic():
        catatan = CatatanKeterlambatan.objects.select_for_update().get(pk=catatan.pk)
        if catatan.tugas_akhir.mahasiswa_id != mahasiswa.pk:
            raise CatatanKeterlambatan.DoesNotExist
        if catatan.status_penilaian == CatatanKeterlambatan.StatusPenilaian.DIBATALKAN:
            raise ValidationError("Catatan yang dibatalkan tidak dapat diajukan keberatan.")

        keberatan = Keberatan.objects.select_for_update().filter(catatan=catatan).first()
        if keberatan and keberatan.status not in {
            Keberatan.Status.DRAF,
            Keberatan.Status.PERLU_KELENGKAPAN,
        }:
            raise ValidationError("Keberatan untuk catatan ini sudah pernah diajukan dan tidak dapat diajukan dua kali.")

        baru = keberatan is None
        if baru:
            keberatan = Keberatan(catatan=catatan)
        sebelum = snapshot(keberatan) if not baru else None
        bukti_lama = keberatan.bukti.name if keberatan.bukti else ""
        keberatan.alasan = alasan
        if bukti is not None:
            keberatan.bukti = bukti
            keberatan.nama_bukti = nama_bukti
            keberatan.ukuran_bukti = ukuran_bukti
        if aksi == "ajukan":
            keberatan.status = Keberatan.Status.DIAJUKAN
            keberatan.diajukan_pada = timezone.now()
        else:
            keberatan.status = Keberatan.Status.DRAF
        keberatan.save()

        if bukti is not None and bukti_lama and bukti_lama != keberatan.bukti.name:
            keberatan.bukti.storage.delete(bukti_lama)

        if aksi == "ajukan":
            catatan_sebelum = snapshot(catatan)
            catatan.status_penilaian = CatatanKeterlambatan.StatusPenilaian.KEBERATAN_DITINJAU
            catatan.save(update_fields=["status_penilaian", "diubah_pada"])
            catat_audit(
                mahasiswa,
                AuditLog.Aksi.UBAH,
                catatan,
                sebelum=catatan_sebelum,
                sesudah=snapshot(catatan),
                keterangan="Mahasiswa mengajukan keberatan atas catatan keterlambatan.",
            )
            penerima = Penugasan.objects.filter(
                tugas_akhir=catatan.tugas_akhir,
                peran=Penugasan.Peran.UTAMA,
            ).select_related("dosen")
            for relasi in penerima:
                notify(
                    relasi.dosen,
                    Notifikasi.Jenis.KEPUTUSAN_KEBERATAN,
                    "Keberatan denda menunggu tinjauan",
                    f"{mahasiswa.nama_lengkap} mengajukan keberatan atas catatan keterlambatan #{catatan.pk}.",
                    "/dosen/keterlambatan",
                    kunci_idempoten=f"keberatan-keterlambatan:{keberatan.pk}:diajukan:{keberatan.diajukan_pada.isoformat()}",
                )

        catat_audit(
            mahasiswa,
            AuditLog.Aksi.TAMBAH if baru else AuditLog.Aksi.UBAH,
            keberatan,
            sebelum=sebelum,
            sesudah=snapshot(keberatan),
            keterangan="Draf keberatan disimpan." if aksi == "simpan_draf" else "Keberatan diajukan.",
        )
        return keberatan


def konfirmasi_catatan(*, catatan, aktor, catatan_peninjau="", jenis_sanksi=None):
    with transaction.atomic():
        catatan = CatatanKeterlambatan.objects.select_for_update().get(pk=catatan.pk)
        if catatan.status_penilaian != CatatanKeterlambatan.StatusPenilaian.USULAN:
            raise ValidationError("Hanya usulan yang belum diajukan keberatan yang dapat ditetapkan.")
        sebelum = snapshot(catatan)
        catatan.status_penilaian = CatatanKeterlambatan.StatusPenilaian.DITETAPKAN
        catatan.catatan_peninjau = (catatan_peninjau or "").strip()
        catatan.ditinjau_oleh = aktor
        catatan.ditinjau_pada = timezone.now()
        catatan.save()

        if jenis_sanksi is not None:
            if not jenis_sanksi.aktif:
                raise ValidationError({"jenis_sanksi_id": "Jenis sanksi yang dipilih sudah tidak aktif."})
            sanksi = SanksiTercatat.objects.filter(catatan=catatan).first()
            if sanksi:
                sanksi.jenis_sanksi = jenis_sanksi
                sanksi.dicatat_oleh = aktor
                sanksi.save(update_fields=["jenis_sanksi", "dicatat_oleh"])
                catat_audit(
                    aktor,
                    AuditLog.Aksi.UBAH,
                    sanksi,
                    sebelum={"jenis_sanksi_id": sebelum.get("jenis_sanksi_id")},
                    sesudah={"jenis_sanksi_id": jenis_sanksi.pk},
                    keterangan="Sanksi akademik pada catatan keterlambatan diperbarui.",
                )
            else:
                sanksi = SanksiTercatat.objects.create(
                    catatan=catatan,
                    jenis_sanksi=jenis_sanksi,
                    dicatat_oleh=aktor,
                )
                catat_audit(
                    aktor,
                    AuditLog.Aksi.TAMBAH,
                    sanksi,
                    sesudah=snapshot(sanksi),
                    keterangan="Sanksi akademik dicatat terpisah dari nominal denda.",
                )

        catat_audit(
            aktor,
            AuditLog.Aksi.UBAH,
            catatan,
            sebelum=sebelum,
            sesudah=snapshot(catatan),
            keterangan="Usulan keterlambatan ditetapkan oleh peninjau.",
        )
        return catatan


def batalkan_catatan(*, catatan, aktor, catatan_peninjau=""):
    with transaction.atomic():
        catatan = CatatanKeterlambatan.objects.select_for_update().get(pk=catatan.pk)
        if catatan.status_penilaian == CatatanKeterlambatan.StatusPenilaian.DIBATALKAN:
            return catatan
        sebelum = snapshot(catatan)
        catatan.status_penilaian = CatatanKeterlambatan.StatusPenilaian.DIBATALKAN
        catatan.catatan_peninjau = (catatan_peninjau or "").strip()
        catatan.ditinjau_oleh = aktor
        catatan.ditinjau_pada = timezone.now()
        catatan.save()
        catat_audit(
            aktor,
            AuditLog.Aksi.UBAH,
            catatan,
            sebelum=sebelum,
            sesudah=snapshot(catatan),
            keterangan="Catatan keterlambatan dibatalkan.",
        )
        return catatan


def putuskan_keberatan(*, keberatan, aktor, aksi, catatan_peninjau=""):
    if aksi not in {"terima", "minta_kelengkapan"}:
        raise ValidationError({"aksi": "Aksi harus terima atau minta_kelengkapan."})
    with transaction.atomic():
        keberatan = (
            Keberatan.objects.select_for_update()
            .select_related("catatan__tugas_akhir__mahasiswa")
            .get(pk=keberatan.pk)
        )
        if keberatan.status != Keberatan.Status.DIAJUKAN:
            raise ValidationError("Keberatan ini tidak sedang menunggu tinjauan.")
        sebelum = snapshot(keberatan)
        keberatan.catatan_peninjau = (catatan_peninjau or "").strip()
        keberatan.ditinjau_oleh = aktor
        keberatan.ditinjau_pada = timezone.now()
        keberatan.status = (
            Keberatan.Status.DITERIMA
            if aksi == "terima"
            else Keberatan.Status.PERLU_KELENGKAPAN
        )
        keberatan.save()
        catat_audit(
            aktor,
            AuditLog.Aksi.UBAH,
            keberatan,
            sebelum=sebelum,
            sesudah=snapshot(keberatan),
            keterangan="Keberatan diterima." if aksi == "terima" else "Mahasiswa diminta melengkapi keberatan.",
        )

        if aksi == "terima":
            catatan = keberatan.catatan
            catatan_sebelum = snapshot(catatan)
            catatan.status_penilaian = CatatanKeterlambatan.StatusPenilaian.DIBATALKAN
            catatan.catatan_peninjau = keberatan.catatan_peninjau
            catatan.ditinjau_oleh = aktor
            catatan.ditinjau_pada = timezone.now()
            catatan.save()
            catat_audit(
                aktor,
                AuditLog.Aksi.UBAH,
                catatan,
                sebelum=catatan_sebelum,
                sesudah=snapshot(catatan),
                keterangan="Catatan keterlambatan dibatalkan karena keberatan diterima.",
            )
            judul = "Keberatan denda diterima"
            isi = f"Keberatan Anda untuk catatan keterlambatan #{catatan.pk} diterima. Catatan telah dibatalkan."
        else:
            catatan = keberatan.catatan
            judul = "Keberatan perlu dilengkapi"
            isi = keberatan.catatan_peninjau or "Dosen meminta kelengkapan untuk keberatan Anda."

        notify(
            catatan.tugas_akhir.mahasiswa,
            Notifikasi.Jenis.KEPUTUSAN_KEBERATAN,
            judul,
            isi,
            "/mahasiswa/denda",
            kunci_idempoten=f"keputusan-keberatan:{keberatan.pk}:{keberatan.status}",
        )
        return keberatan


def ringkasan_denda(tugas_akhir_ids, *, periode_ids=None):
    if not tugas_akhir_ids:
        return None
    catatan_qs = CatatanKeterlambatan.objects.filter(tugas_akhir_id__in=tugas_akhir_ids)
    catatan_aktif = list(
        catatan_qs.exclude(
            status_penilaian=CatatanKeterlambatan.StatusPenilaian.DIBATALKAN
        )
    )
    # Ringkasan menghitung ulang tanggal berjalan agar selalu sama dengan rumus
    # yang dipakai API detail, meskipun job Celery harian belum berjalan hari ini.
    jumlah_total = sum(_hitung_dari_catatan(item)["nominal"] for item in catatan_aktif)
    jumlah_terbuka = catatan_qs.filter(status_penilaian__in=STATUS_TERBUKA).count()
    keberatan_ditinjau = catatan_qs.filter(
        status_penilaian=CatatanKeterlambatan.StatusPenilaian.KEBERATAN_DITINJAU
    ).count()
    konfigurasi_qs = KonfigurasiDenda.objects.filter(periode__tugas_akhir__id__in=tugas_akhir_ids)
    if periode_ids is not None:
        konfigurasi_qs = KonfigurasiDenda.objects.filter(periode_id__in=periode_ids)
    ada_data = catatan_qs.exists() or konfigurasi_qs.exists()
    if not ada_data:
        return None
    return {
        "total_nominal": jumlah_total,
        "keterlambatan_terbuka": jumlah_terbuka,
        "keberatan_ditinjau": keberatan_ditinjau,
        "jumlah_catatan": catatan_qs.count(),
        "label_simulasi": konfigurasi_qs.filter(label_simulasi=True).exists(),
    }


def ringkasan_denda_mahasiswa(tugas_akhir):
    if tugas_akhir is None:
        return None
    return ringkasan_denda([tugas_akhir.pk], periode_ids=[tugas_akhir.periode_id])


def ringkasan_denda_dosen(dosen):
    ta_ids = list(
        Penugasan.objects.filter(
            dosen=dosen,
            peran=Penugasan.Peran.UTAMA,
            tugas_akhir__status=TugasAkhir.Status.AKTIF,
        ).values_list("tugas_akhir_id", flat=True)
    )
    periode_ids = list(
        TugasAkhir.objects.filter(pk__in=ta_ids).values_list("periode_id", flat=True).distinct()
    )
    return ringkasan_denda(ta_ids, periode_ids=periode_ids)


def sanksi_milestone(tugas_akhir_id, milestone_id):
    sanksi = (
        SanksiTercatat.objects.filter(
            catatan__tugas_akhir_id=tugas_akhir_id,
            catatan__milestone_id=milestone_id,
            catatan__status_penilaian=CatatanKeterlambatan.StatusPenilaian.DITETAPKAN,
        )
        .select_related("jenis_sanksi")
        .order_by("-dibuat_pada", "-id")
        .first()
    )
    return sanksi.jenis_sanksi.nama if sanksi else None


def catatan_boleh_diakses(user, catatan):
    if not user.is_authenticated or not user.is_active:
        return False
    if user.role == Role.ADMIN:
        return True
    if user.role == Role.MAHASISWA:
        return catatan.tugas_akhir.mahasiswa_id == user.pk
    if user.role == Role.DOSEN:
        return _penugasan_utama(catatan.tugas_akhir, user)
    return False


def keberatan_boleh_diakses(user, keberatan):
    return catatan_boleh_diakses(user, keberatan.catatan)
