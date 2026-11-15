from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.http import Http404
from django.utils import timezone

from akademik.models import Penugasan
from dokumen.models import DokumenVersi
from dokumen.services import url_pratinjau, url_unduh
from notifikasi.models import Notifikasi
from notifikasi.services import notify

from .models import ChecklistRevisi, Review

PERAN_REVIEW = (Penugasan.Peran.UTAMA, Penugasan.Peran.PENDAMPING)


class ReviewError(Exception):
    """Pelanggaran aturan review yang aman dikembalikan sebagai respons API."""


def versi_untuk_pembimbing(user, versi_id=None):
    qs = (
        DokumenVersi.objects.select_related(
            "dokumen__milestone__tugas_akhir__mahasiswa",
            "dokumen__milestone__tugas_akhir__periode",
        )
        .filter(
            dokumen__milestone__tugas_akhir__penugasan__dosen=user,
            dokumen__milestone__tugas_akhir__penugasan__peran__in=PERAN_REVIEW,
        )
    )
    return qs.filter(pk=versi_id) if versi_id is not None else qs


def review_terbit_milik_mahasiswa(user, review_id=None):
    qs = Review.objects.filter(
        status=Review.Status.TERBIT,
        versi__dokumen__milestone__tugas_akhir__mahasiswa=user,
    ).select_related(
        "pemberi",
        "versi__dokumen__milestone__tugas_akhir__mahasiswa",
        "versi__dokumen__milestone",
    )
    return qs.filter(pk=review_id) if review_id is not None else qs


def _payload_review(review):
    return {
        "id": review.pk,
        "pemberi": {"nama_lengkap": review.pemberi.nama_lengkap},
        "bagian": review.bagian,
        "komentar": review.komentar,
        "nilai": review.nilai,
        "rekomendasi": review.rekomendasi,
        "rekomendasi_label": review.get_rekomendasi_display() if review.rekomendasi else None,
        "tenggat_revisi": review.tenggat_revisi,
        "diterbitkan_pada": review.diterbitkan_pada,
    }


def detail_dosen(user, versi_id):
    versi = versi_untuk_pembimbing(user, versi_id).first()
    if versi is None:
        raise Http404

    ta = versi.dokumen.milestone.tugas_akhir
    draf = (
        Review.objects.filter(versi=versi, pemberi=user, status=Review.Status.DRAF)
        .order_by("-diubah_pada", "-id")
        .first()
    )
    terbit = (
        Review.objects.filter(versi=versi, status=Review.Status.TERBIT)
        .select_related("pemberi")
        .order_by("-diterbitkan_pada", "-id")
    )
    ekstensi = versi.nama_asli.rsplit(".", 1)[-1].lower() if "." in versi.nama_asli else ""
    return {
        "versi": {
            "id": versi.pk,
            "nama_asli": versi.nama_asli,
            "nomor_versi": versi.nomor_versi,
            "halaman": versi.halaman,
            "ukuran": versi.ukuran,
            "status": versi.status,
            "catatan_mahasiswa": versi.catatan,
            "diunggah_pada": versi.diunggah_pada,
            "ekstensi": ekstensi,
            "unduh_url": url_unduh(user, versi),
            "pratinjau_url": url_pratinjau(user, versi),
            "milestone": {
                "id": versi.dokumen.milestone_id,
                "urutan": versi.dokumen.milestone.urutan,
                "nama": versi.dokumen.milestone.nama,
            },
        },
        "mahasiswa": {
            "identifier": ta.mahasiswa.identifier,
            "nama_lengkap": ta.mahasiswa.nama_lengkap,
        },
        "tugas_akhir": {
            "id": ta.pk,
            "judul": ta.judul,
            "jenis_penelitian": ta.jenis_penelitian,
        },
        "draf": {
            "id": draf.pk,
            "bagian": draf.bagian,
            "komentar": draf.komentar,
            "nilai": draf.nilai,
            "rekomendasi": draf.rekomendasi,
            "tenggat_revisi": draf.tenggat_revisi,
            "bagikan_catatan_awal": draf.bagikan_catatan_awal,
            "diubah_pada": draf.diubah_pada,
        } if draf else None,
        "catatan_sebelumnya": [_payload_review(item) for item in terbit],
    }


@transaction.atomic
def simpan_draf(*, user, versi_id, data):
    versi = versi_untuk_pembimbing(user, versi_id).select_for_update().first()
    if versi is None:
        raise Http404

    draf = (
        Review.objects.select_for_update()
        .filter(versi=versi, pemberi=user, status=Review.Status.DRAF)
        .first()
    )
    if draf is None:
        draf = Review(versi=versi, pemberi=user, status=Review.Status.DRAF)

    for field, value in data.items():
        setattr(draf, field, value)
    draf.save()
    return draf


@transaction.atomic
def terbitkan_review(*, user, review_id):
    dasar = Review.objects.filter(
        pk=review_id,
        pemberi=user,
        versi__dokumen__milestone__tugas_akhir__penugasan__dosen=user,
        versi__dokumen__milestone__tugas_akhir__penugasan__peran__in=PERAN_REVIEW,
    ).values("versi_id").first()
    if dasar is None:
        raise Http404

    # Urutan penguncian versi -> review sama dengan simpan_draf(), menghindari
    # perlombaan antara autosave dan proses penerbitan untuk versi yang sama.
    versi = DokumenVersi.objects.select_for_update().get(pk=dasar["versi_id"])
    review = (
        Review.objects.select_for_update()
        .select_related("pemberi")
        .get(pk=review_id, pemberi=user, versi=versi)
    )

    # Retry POST untuk review yang sama mengembalikan hasil semula tanpa notifikasi baru.
    if review.status == Review.Status.TERBIT:
        return review, True

    if not review.rekomendasi:
        raise ReviewError("Pilih rekomendasi Perlu revisi atau Disetujui sebelum menerbitkan feedback.")
    if review.rekomendasi == Review.Rekomendasi.PERLU_REVISI and not review.komentar.strip():
        raise ReviewError("Komentar dan arahan wajib diisi untuk rekomendasi Perlu revisi.")

    review.status = Review.Status.TERBIT
    review.diterbitkan_pada = timezone.now()
    review.save()

    versi.status = (
        DokumenVersi.Status.PERLU_REVISI
        if review.rekomendasi == Review.Rekomendasi.PERLU_REVISI
        else DokumenVersi.Status.DISETUJUI
    )
    versi.save(update_fields={"status"})

    mahasiswa = versi.dokumen.milestone.tugas_akhir.mahasiswa
    label = review.get_rekomendasi_display()
    notify(
        mahasiswa,
        Notifikasi.Jenis.REVIEW_TERBIT,
        "Review dokumen diterbitkan",
        f"Pembimbing menerbitkan review {label.lower()} untuk {versi.dokumen.milestone.nama} (versi {versi.nomor_versi}).",
        f"/mahasiswa/review/{review.pk}",
    )
    return review, False


def daftar_review_mahasiswa(user):
    """Daftar hanya review terbit, plus catatan awal yang memang dibagikan secara eksplisit."""
    from dokumen.services import ta_saya

    ta = ta_saya(user)
    jika_tidak_ada = {"tugas_akhir": None, "hasil": [], "menunggu_review": []}
    if ta is None:
        return jika_tidak_ada

    terbit = review_terbit_milik_mahasiswa(user).filter(
        versi__dokumen__milestone__tugas_akhir=ta
    ).order_by("-diterbitkan_pada", "-id")
    hasil = []
    for review in terbit:
        versi = review.versi
        hasil.append({
            **_payload_review(review),
            "versi": {
                "id": versi.pk,
                "nama_asli": versi.nama_asli,
                "nomor_versi": versi.nomor_versi,
                "status": versi.status,
                "halaman": versi.halaman,
                "ukuran": versi.ukuran,
                "unduh_url": url_unduh(user, versi),
                "milestone": {
                    "id": versi.dokumen.milestone_id,
                    "urutan": versi.dokumen.milestone.urutan,
                    "nama": versi.dokumen.milestone.nama,
                },
            },
        })

    menunggu = []
    versi_menunggu = DokumenVersi.objects.filter(
        dokumen__milestone__tugas_akhir=ta,
        status=DokumenVersi.Status.MENUNGGU_REVIEW,
    ).select_related("dokumen__milestone")
    for versi in versi_menunggu:
        catatan = (
            Review.objects.filter(
                versi=versi, status=Review.Status.DRAF, bagikan_catatan_awal=True
            )
            .exclude(komentar="")
            .order_by("-diubah_pada", "-id")
            .first()
        )
        menunggu.append({
            "versi": {
                "id": versi.pk,
                "nama_asli": versi.nama_asli,
                "nomor_versi": versi.nomor_versi,
                "status": versi.status,
                "halaman": versi.halaman,
                "ukuran": versi.ukuran,
                "milestone": {
                    "id": versi.dokumen.milestone_id,
                    "urutan": versi.dokumen.milestone.urutan,
                    "nama": versi.dokumen.milestone.nama,
                },
            },
            # Sengaja hanya memuat bagian+komentar, tidak mengekspos objek draf, nilai,
            # rekomendasi, tenggat, pemberi, ataupun ID review internal.
            "catatan_awal": {
                "bagian": catatan.bagian,
                "komentar": catatan.komentar,
                "label": "Bukan review final",
            } if catatan else None,
        })

    return {
        "tugas_akhir": {"id": ta.pk, "judul": ta.judul},
        "hasil": hasil,
        "menunggu_review": menunggu,
    }


def detail_review_mahasiswa(user, review_id):
    review = review_terbit_milik_mahasiswa(user, review_id).first()
    if review is None:
        raise Http404
    versi = review.versi
    ta = versi.dokumen.milestone.tugas_akhir
    semua_review = review_terbit_milik_mahasiswa(user).filter(
        versi__dokumen__milestone__tugas_akhir=ta
    ).exclude(pk=review.pk).order_by("-diterbitkan_pada", "-id")
    checklist = ChecklistRevisi.objects.filter(review=review, mahasiswa=user)
    return {
        "review": _payload_review(review),
        "versi": {
            "id": versi.pk,
            "nama_asli": versi.nama_asli,
            "nomor_versi": versi.nomor_versi,
            "status": versi.status,
            "halaman": versi.halaman,
            "ukuran": versi.ukuran,
            "ekstensi": versi.nama_asli.rsplit(".", 1)[-1].lower() if "." in versi.nama_asli else "",
            "unduh_url": url_unduh(user, versi),
            "pratinjau_url": url_pratinjau(user, versi),
            "milestone": {
                "id": versi.dokumen.milestone_id,
                "urutan": versi.dokumen.milestone.urutan,
                "nama": versi.dokumen.milestone.nama,
            },
        },
        "tugas_akhir": {"id": ta.pk, "judul": ta.judul},
        "riwayat_feedback": [
            {
                **_payload_review(item),
                "versi": {
                    "id": item.versi_id,
                    "nama_asli": item.versi.nama_asli,
                    "nomor_versi": item.versi.nomor_versi,
                    "milestone": {
                        "urutan": item.versi.dokumen.milestone.urutan,
                        "nama": item.versi.dokumen.milestone.nama,
                    },
                },
            }
            for item in semua_review
        ],
        "checklist": [
            {
                "id": item.pk,
                "catatan": item.catatan,
                "selesai": item.selesai,
                "dibuat_pada": item.dibuat_pada,
                "diubah_pada": item.diubah_pada,
            }
            for item in checklist
        ],
    }


def review_mahasiswa_terjangkau(user, review_id):
    review = review_terbit_milik_mahasiswa(user, review_id).first()
    if review is None:
        raise Http404
    return review


def checklist_mahasiswa_terjangkau(user, checklist_id):
    checklist = (
        ChecklistRevisi.objects.select_related("review__versi__dokumen__milestone__tugas_akhir")
        .filter(
            pk=checklist_id,
            mahasiswa=user,
            review__status=Review.Status.TERBIT,
            review__versi__dokumen__milestone__tugas_akhir__mahasiswa=user,
        )
        .first()
    )
    if checklist is None:
        raise Http404
    return checklist

def daftar_review_dosen(user):
    """Antrean versi dokumen yang masih perlu ditinjau oleh dosen ini.

    Hanya pembimbing utama dan pendamping yang memperoleh versi melalui
    ``versi_untuk_pembimbing``. Draf milik dosen lain tidak pernah disertakan.
    Versi yang sudah diterbitkan oleh dosen yang sedang masuk dikeluarkan dari
    antreannya; draf miliknya sendiri tetap muncul sebagai "Lanjutkan draf".
    """
    draf_sendiri = Review.objects.filter(
        versi_id=OuterRef("pk"), pemberi=user, status=Review.Status.DRAF
    )
    review_sendiri_terbit = Review.objects.filter(
        versi_id=OuterRef("pk"), pemberi=user, status=Review.Status.TERBIT
    )
    versi_list = list(
        versi_untuk_pembimbing(user)
        .annotate(
            punya_draf_sendiri=Exists(draf_sendiri),
            sudah_diterbitkan_sendiri=Exists(review_sendiri_terbit),
        )
        .filter(
            Q(status=DokumenVersi.Status.MENUNGGU_REVIEW)
            | Q(punya_draf_sendiri=True)
        )
        .filter(sudah_diterbitkan_sendiri=False)
        .select_related(
            "dokumen__milestone__tugas_akhir__mahasiswa",
            "dokumen__milestone__tugas_akhir__periode",
        )
        .order_by("diunggah_pada", "pk")
        .distinct()
    )

    if not versi_list:
        return {"jumlah": 0, "jumlah_menunggu": 0, "jumlah_draf": 0, "hasil": []}

    draf_map = {
        item.versi_id: item
        for item in Review.objects.filter(
            versi_id__in=[versi.pk for versi in versi_list],
            pemberi=user,
            status=Review.Status.DRAF,
        ).order_by("-diubah_pada", "-id")
    }

    hasil = []
    for versi in versi_list:
        milestone = versi.dokumen.milestone
        ta = milestone.tugas_akhir
        draf = draf_map.get(versi.pk)
        hasil.append({
            "versi": {
                "id": versi.pk,
                "nama_asli": versi.nama_asli,
                "nomor_versi": versi.nomor_versi,
                "halaman": versi.halaman,
                "ukuran": versi.ukuran,
                "status": versi.status,
                "diunggah_pada": versi.diunggah_pada,
                "milestone": {
                    "id": milestone.pk,
                    "urutan": milestone.urutan,
                    "nama": milestone.nama,
                },
            },
            "mahasiswa": {
                "identifier": ta.mahasiswa.identifier,
                "nama_lengkap": ta.mahasiswa.nama_lengkap,
            },
            "tugas_akhir": {
                "id": ta.pk,
                "judul": ta.judul,
                "jenis_penelitian": ta.jenis_penelitian,
            },
            "draf": {"id": draf.pk, "diubah_pada": draf.diubah_pada} if draf else None,
        })

    return {
        "jumlah": len(hasil),
        "jumlah_menunggu": sum(1 for item in hasil if item["versi"]["status"] == DokumenVersi.Status.MENUNGGU_REVIEW),
        "jumlah_draf": sum(1 for item in hasil if item["draf"] is not None),
        "hasil": hasil,
    }
