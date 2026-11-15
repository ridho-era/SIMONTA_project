"""Query dan agregasi F-02, F-11, F-12. Tidak menyimpan status turunan ke database."""
from collections import defaultdict
from datetime import date
from enum import Enum

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from akademik.models import KonfigurasiDenda, Penugasan, TugasAkhir
from keterlambatan.models import CatatanKeterlambatan
from dokumen.models import DokumenVersi
from milestone.models import Milestone
from milestone.services import Status as StatusMilestone, bangun_timeline
from review.models import Review
from review.services import PERAN_REVIEW, daftar_review_dosen
from jadwal.services import bimbingan_terdekat_mahasiswa, permohonan_jadwal_dashboard_dosen


class StatusMahasiswa(str, Enum):
    MENUNGGU_REVIEW = "menunggu_review"
    TERLAMBAT = "terlambat"
    BERJALAN = "berjalan"
    SELESAI = "selesai"
    DIBATALKAN = "dibatalkan"


LABEL_STATUS_MAHASISWA = {
    StatusMahasiswa.MENUNGGU_REVIEW.value: "Menunggu Review",
    StatusMahasiswa.TERLAMBAT.value: "Terlambat",
    StatusMahasiswa.BERJALAN.value: "Berjalan",
    StatusMahasiswa.SELESAI.value: "Selesai",
    StatusMahasiswa.DIBATALKAN.value: "Dibatalkan",
}

URUTAN_DIIZINKAN = {"nama", "progres", "target", "terbaru"}
TAB_DIIZINKAN = {"semua", "menunggu_review", "terlambat"}
BARIS_PER_HALAMAN = 20


def _iso(nilai):
    return nilai.isoformat() if nilai else None


def _milestone_payload(item):
    return {
        "id": item.id,
        "urutan": item.urutan,
        "nama": item.nama,
        "bobot": float(item.bobot),
        "target": _iso(item.target),
        "status": item.status,
        "tahap_aktif": item.tahap_aktif,
        "terkunci": item.terkunci,
        "tingkat_penyelesaian": item.tingkat_penyelesaian,
        "diverifikasi_pada": _iso(item.diverifikasi_pada),
    }


def _ambil_ta_terkini(ta_list):
    """Satu TA per mahasiswa: prioritaskan TA aktif, kemudian TA terbaru."""
    pilihan = {}
    for ta in ta_list:
        skor = (ta.status == TugasAkhir.Status.AKTIF, ta.dibuat_pada, ta.pk)
        lama = pilihan.get(ta.mahasiswa_id)
        if lama is None or skor > lama[0]:
            pilihan[ta.mahasiswa_id] = (skor, ta)
    return sorted((item[1] for item in pilihan.values()), key=lambda x: x.mahasiswa.nama_lengkap.casefold())


def _kumpulan_ta_dosen(user, search=""):
    qs = (
        TugasAkhir.objects.filter(
            penugasan__dosen=user,
            penugasan__peran__in=PERAN_REVIEW,
        )
        .select_related("mahasiswa", "periode")
        .distinct()
    )
    search = (search or "").strip()
    if search:
        qs = qs.filter(
            Q(mahasiswa__nama_lengkap__icontains=search)
            | Q(mahasiswa__identifier__icontains=search)
        )
    return _ambil_ta_terkini(list(qs.order_by("mahasiswa_id", "-dibuat_pada", "-id")))


def _bangun_baris_ta(ta_list, dosen=None):
    """Membangun status/progres dari milestone dan unggahan yang benar-benar tersimpan."""
    if not ta_list:
        return []

    ta_ids = [ta.pk for ta in ta_list]
    milestone_map = defaultdict(list)
    milestone_models = list(
        Milestone.objects.filter(tugas_akhir_id__in=ta_ids).order_by("tugas_akhir_id", "urutan", "id")
    )
    for milestone in milestone_models:
        milestone_map[milestone.tugas_akhir_id].append(milestone)

    versi_menunggu = list(
        DokumenVersi.objects.filter(
            dokumen__milestone__tugas_akhir_id__in=ta_ids,
            status=DokumenVersi.Status.MENUNGGU_REVIEW,
        )
        .select_related("dokumen__milestone")
        .order_by("diunggah_pada", "id")
    )
    versi_menunggu_per_ta = {}
    for versi in versi_menunggu:
        ta_id = versi.dokumen.milestone.tugas_akhir_id
        versi_menunggu_per_ta.setdefault(ta_id, versi)

    versi_terbaru = list(
        DokumenVersi.objects.filter(dokumen__milestone__tugas_akhir_id__in=ta_ids)
        .select_related("dokumen__milestone")
        .order_by("-diunggah_pada", "-id")
    )
    versi_terbaru_per_ta = {}
    for versi in versi_terbaru:
        ta_id = versi.dokumen.milestone.tugas_akhir_id
        versi_terbaru_per_ta.setdefault(ta_id, versi)

    assignment_map = defaultdict(list)
    if dosen is None:
        assignments = Penugasan.objects.filter(tugas_akhir_id__in=ta_ids).select_related("dosen").order_by("peran", "dosen__nama_lengkap")
    else:
        assignments = Penugasan.objects.filter(
            tugas_akhir_id__in=ta_ids,
            tugas_akhir__penugasan__dosen=dosen,
            peran__in=PERAN_REVIEW,
        ).select_related("dosen").order_by("peran", "dosen__nama_lengkap").distinct()
    for assignment in assignments:
        assignment_map[assignment.tugas_akhir_id].append(assignment)

    rows = []
    hari_ini = timezone.localdate()
    for ta in ta_list:
        daftar_milestone = milestone_map[ta.pk]
        timeline = bangun_timeline(daftar_milestone, hari_ini)
        active_item = next((item for item in timeline.items if item.tahap_aktif), None)
        active_model = next((m for m in daftar_milestone if active_item and m.pk == active_item.id), None)
        # TA yang sudah selesai/dibatalkan tidak lagi dihitung terlambat meskipun
        # target milestone historisnya berada di masa lalu.
        late_items = (
            [item for item in timeline.items if item.status == StatusMilestone.TERLAMBAT]
            if ta.status == TugasAkhir.Status.AKTIF
            else []
        )
        versi_waiting = versi_menunggu_per_ta.get(ta.pk)

        if ta.status == TugasAkhir.Status.SELESAI:
            status_value = StatusMahasiswa.SELESAI.value
        elif ta.status == TugasAkhir.Status.DIBATALKAN:
            status_value = StatusMahasiswa.DIBATALKAN.value
        elif late_items:
            status_value = StatusMahasiswa.TERLAMBAT.value
        elif versi_waiting:
            status_value = StatusMahasiswa.MENUNGGU_REVIEW.value
        else:
            status_value = StatusMahasiswa.BERJALAN.value

        pembimbing = [
            {
                "id": item.dosen_id,
                "identifier": item.dosen.identifier,
                "nama_lengkap": item.dosen.nama_lengkap,
                "peran": item.peran,
                "peran_label": item.get_peran_display(),
            }
            for item in assignment_map[ta.pk]
        ]

        rows.append({
            "id": ta.pk,
            "mahasiswa": {
                "id": ta.mahasiswa_id,
                "identifier": ta.mahasiswa.identifier,
                "nama_lengkap": ta.mahasiswa.nama_lengkap,
            },
            "tugas_akhir": {
                "id": ta.pk,
                "judul": ta.judul,
                "jenis_penelitian": ta.jenis_penelitian,
                "status": ta.status,
                "periode": ta.periode.label,
            },
            "status": status_value,
            "status_label": LABEL_STATUS_MAHASISWA[status_value],
            "progres": float(timeline.progres),
            "jumlah_diverifikasi": timeline.jumlah_diverifikasi,
            "total_milestone": len(timeline.items),
            "tahap_aktif": _milestone_payload(active_item) if active_item else None,
            "milestone": [_milestone_payload(item) for item in timeline.items],
            "menunggu_review": bool(versi_waiting),
            "versi_menunggu": {
                "id": versi_waiting.pk,
                "nama_asli": versi_waiting.nama_asli,
                "diunggah_pada": _iso(versi_waiting.diunggah_pada),
            } if versi_waiting else None,
            "pembimbing": pembimbing,
            "can_manage_milestone": bool(dosen and any(
                item.dosen_id == dosen.pk and item.peran == Penugasan.Peran.UTAMA
                for item in assignment_map[ta.pk]
            )),
            "can_review": bool(dosen and any(item.dosen_id == dosen.pk for item in assignment_map[ta.pk])),
            "_target_aktif": active_model.target if active_model else None,
            "_dibuat_pada": ta.dibuat_pada,
            "_unggah_pada": versi_terbaru_per_ta[ta.pk].diunggah_pada if ta.pk in versi_terbaru_per_ta else ta.dibuat_pada,
            "_terlambat": bool(late_items),
        })
    return rows


def dashboard_mahasiswa(user):
    from dokumen.services import ta_saya

    ta = ta_saya(user)
    kosong = {
        "mahasiswa": {"id": user.pk, "identifier": user.identifier, "nama_lengkap": user.nama_lengkap},
        "tugas_akhir": None,
        "progres": 0,
        "jumlah_diverifikasi": 0,
        "total_milestone": 0,
        "tahap_aktif": None,
        "milestone": [],
        "tim_pembimbing": [],
        "review_tindak_lanjut": None,
        "banner_keterlambatan": None,
        "bimbingan_terdekat": bimbingan_terdekat_mahasiswa(ta),
        "ringkasan_denda": None,
    }
    if ta is None:
        return kosong

    baris = _bangun_baris_ta([ta])[0]
    assignments = Penugasan.objects.filter(
        tugas_akhir=ta,
        peran__in=PERAN_REVIEW,
    ).select_related("dosen").order_by("peran", "dosen__nama_lengkap")
    tim = [
        {
            "id": item.dosen_id,
            "identifier": item.dosen.identifier,
            "nama_lengkap": item.dosen.nama_lengkap,
            "peran": item.peran,
            "peran_label": item.get_peran_display(),
        }
        for item in assignments
    ]

    review = (
        Review.objects.filter(
            versi__dokumen__milestone__tugas_akhir=ta,
            status=Review.Status.TERBIT,
            rekomendasi=Review.Rekomendasi.PERLU_REVISI,
        )
        .select_related("pemberi", "versi__dokumen__milestone")
        .order_by("-diterbitkan_pada", "-id")
        .first()
    )
    review_payload = None
    if review:
        review_payload = {
            "id": review.pk,
            "pemberi": review.pemberi.nama_lengkap,
            "komentar": review.komentar,
            "bagian": review.bagian,
            "nilai": review.nilai,
            "tenggat_revisi": _iso(review.tenggat_revisi),
            "milestone": review.versi.dokumen.milestone.nama,
            "nama_berkas": review.versi.nama_asli,
            "url": f"/mahasiswa/review/{review.pk}",
        }

    overdue = next((item for item in baris["milestone"] if item["status"] == StatusMilestone.TERLAMBAT), None)
    banner = None
    if overdue:
        banner = {
            "milestone": {"id": overdue["id"], "nama": overdue["nama"]},
            "target": overdue["target"],
            # Modul sanksi belum dibangun; tidak mengarang sanksi.
            "sanksi_akademik": None,
        }

    return {
        **kosong,
        "tugas_akhir": {
            "id": ta.pk,
            "judul": ta.judul,
            "jenis_penelitian": ta.jenis_penelitian,
            "status": ta.status,
            "periode": ta.periode.label,
        },
        "progres": baris["progres"],
        "jumlah_diverifikasi": baris["jumlah_diverifikasi"],
        "total_milestone": baris["total_milestone"],
        "tahap_aktif": baris["tahap_aktif"],
        "milestone": baris["milestone"],
        "tim_pembimbing": tim,
        "review_tindak_lanjut": review_payload,
        "banner_keterlambatan": banner,
        # Jadwal terdekat berasal dari modul jadwal; ringkasan denda belum dibangun.
        "bimbingan_terdekat": bimbingan_terdekat_mahasiswa(ta),
        "ringkasan_denda": None,
    }


def dashboard_dosen(user):
    ta_list = _kumpulan_ta_dosen(user)
    rows = _bangun_baris_ta(ta_list, dosen=user)
    antrean = daftar_review_dosen(user)

    # Hitung mahasiswa unik yang terlambat berdasarkan dua sumber:
    # milestone aktif yang melewati target, serta catatan keterlambatan yang
    # belum dibatalkan pada TA aktif yang pembimbing utamanya adalah dosen ini.
    # Catatan dibatasi ke penugasan utama karena keputusan F-14 hanya menjadi
    # kewenangan pembimbing utama. Beberapa catatan milik mahasiswa yang sama
    # tetap dihitung sebagai satu mahasiswa.
    mahasiswa_terlambat_ids = {
        row["mahasiswa"]["id"] for row in rows if row["_terlambat"]
    }
    ta_utama_aktif_ids = Penugasan.objects.filter(
        dosen=user,
        peran=Penugasan.Peran.UTAMA,
        tugas_akhir__status=TugasAkhir.Status.AKTIF,
    ).values_list("tugas_akhir_id", flat=True)
    mahasiswa_catatan_aktif_ids = CatatanKeterlambatan.objects.filter(
        tugas_akhir_id__in=ta_utama_aktif_ids,
    ).exclude(
        status_penilaian=CatatanKeterlambatan.StatusPenilaian.DIBATALKAN,
    ).values_list("tugas_akhir__mahasiswa_id", flat=True).distinct()
    mahasiswa_terlambat_ids.update(mahasiswa_catatan_aktif_ids)

    perhatian = []
    for row in rows:
        if not row["_terlambat"] or not row["tahap_aktif"]:
            continue
        perhatian.append({
            "mahasiswa": row["mahasiswa"],
            "tugas_akhir": row["tugas_akhir"],
            "milestone": row["tahap_aktif"]["nama"],
            "target": row["tahap_aktif"]["target"],
            "sanksi_akademik": None,
        })
    perhatian.sort(key=lambda item: item["target"] or "9999-12-31")

    periode_ids = [ta.periode_id for ta in ta_list]
    label_simulasi = KonfigurasiDenda.objects.filter(
        periode_id__in=periode_ids, label_simulasi=True
    ).exists() if periode_ids else False

    return {
        "dosen": {
            "id": user.pk,
            "identifier": user.identifier,
            "nama_lengkap": user.nama_lengkap,
            "email_akademik": user.email_akademik,
        },
        "statistik": {
            "mahasiswa_bimbingan": len(rows),
            "menunggu_review": antrean["jumlah_menunggu"],
            "terlambat": len(mahasiswa_terlambat_ids),
        },
        "antrean_review": {
            "jumlah": antrean["jumlah"],
            "jumlah_menunggu": antrean["jumlah_menunggu"],
            "jumlah_draf": antrean["jumlah_draf"],
            "hasil": antrean["hasil"][:8],
        },
        "perlu_perhatian": perhatian[:8],
        "jumlah_perlu_perhatian": len(perhatian),
        "permohonan_jadwal": permohonan_jadwal_dashboard_dosen(user),
        "label_simulasi": label_simulasi,
    }


def daftar_mahasiswa_bimbingan(user, params):
    search = params.get("q", "")
    ta_list = _kumpulan_ta_dosen(user, search=search)
    rows = _bangun_baris_ta(ta_list, dosen=user)

    milestone_choices = {}
    for row in rows:
        for item in row["milestone"]:
            milestone_choices[item["id"]] = {
                "id": item["id"],
                "urutan": item["urutan"],
                "nama": item["nama"],
            }
    milestone_choices = sorted(milestone_choices.values(), key=lambda x: (x["urutan"], x["nama"].casefold()))

    milestone_param = params.get("milestone")
    if milestone_param not in (None, ""):
        try:
            milestone_id = int(milestone_param)
        except (TypeError, ValueError):
            raise ValueError("Filter milestone harus berupa ID angka.")
        rows = [row for row in rows if any(item["id"] == milestone_id for item in row["milestone"])]

    status_filter = params.get("status", "")
    if status_filter:
        pilihan = {item.value for item in StatusMahasiswa}
        if status_filter not in pilihan:
            raise ValueError("Filter status tidak dikenal.")
        rows = [row for row in rows if row["status"] == status_filter]

    tab = params.get("tab", "semua") or "semua"
    if tab not in TAB_DIIZINKAN:
        raise ValueError("Tab tidak dikenal.")
    jumlah_semua = len(rows)
    jumlah_menunggu = sum(1 for row in rows if row["menunggu_review"])
    jumlah_terlambat = sum(1 for row in rows if row["_terlambat"])

    if tab == "menunggu_review":
        rows = [row for row in rows if row["menunggu_review"]]
    elif tab == "terlambat":
        rows = [row for row in rows if row["_terlambat"]]

    urut = params.get("urut", "nama") or "nama"
    arah = params.get("arah", "asc") or "asc"
    if urut not in URUTAN_DIIZINKAN:
        raise ValueError("Pilihan urutan tidak dikenal.")
    if arah not in {"asc", "desc"}:
        raise ValueError("Arah urutan tidak dikenal.")

    if urut == "nama":
        key = lambda row: row["mahasiswa"]["nama_lengkap"].casefold()
    elif urut == "progres":
        key = lambda row: row["progres"]
    elif urut == "target":
        kosong_target = date.min if arah == "desc" else date.max
        key = lambda row: row["_target_aktif"] or kosong_target
    else:
        key = lambda row: row["_unggah_pada"]
    rows.sort(key=lambda row: (key(row), row["id"]), reverse=(arah == "desc"))

    return {
        "jumlah": len(rows),
        "jumlah_semua": jumlah_semua,
        "jumlah_menunggu_review": jumlah_menunggu,
        "jumlah_terlambat": jumlah_terlambat,
        "halaman": 1,
        "total_halaman": 1,
        "per_halaman": BARIS_PER_HALAMAN,
        "tab": tab,
        "status_choices": [{"value": item.value, "label": LABEL_STATUS_MAHASISWA[item.value]} for item in StatusMahasiswa],
        "milestone_choices": milestone_choices,
        "hasil": rows,
    }


def paginasi_mahasiswa_bimbingan(payload, halaman):
    paginator = Paginator(payload["hasil"], BARIS_PER_HALAMAN)
    page = paginator.get_page(halaman)
    payload["halaman"] = page.number
    payload["total_halaman"] = paginator.num_pages
    payload["hasil"] = [
        {key: value for key, value in row.items() if not key.startswith("_")}
        for row in page.object_list
    ]
    return payload
