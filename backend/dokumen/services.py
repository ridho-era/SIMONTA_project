from urllib.parse import urlencode

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.db.models import Max, Prefetch
from django.http import Http404

from accounts.models import Role
from akademik.models import Penugasan, TugasAkhir
from milestone.models import Milestone
from milestone.services import bangun_timeline, timeline_ta
from notifikasi.models import Notifikasi
from notifikasi.services import notify
from review.models import Review

from .models import Dokumen, DokumenVersi
from .validators import validasi_berkas

TAUTAN_DOSEN = "/dosen/review"
_penandatangan = TimestampSigner(salt="dokumen.unduh")

# kode penghalang -> (label singkat untuk pilihan di form, pesan lengkap untuk galat 409)
_PENGHALANG = {
    "nonaktif": ("Tugas akhir tidak aktif", "Tugas akhir Anda tidak aktif; unggahan tidak dapat dilakukan."),
    "diverifikasi": (
        "Sudah diverifikasi",
        "Milestone ini sudah diverifikasi pembimbing utama; unggahan baru tidak diterima.",
    ),
    "terkunci": ("Terkunci", "Milestone ini masih terkunci. Tunggu verifikasi tahap sebelumnya."),
}


class UnggahError(Exception):
    """Pelanggaran aturan unggahan; pesannya aman ditampilkan ke pengguna."""


class TokenKedaluwarsa(Exception):
    pass


class TokenTidakValid(Exception):
    pass


def ta_saya(user):
    """TA aktif milik mahasiswa, atau yang terbaru bila tidak ada yang aktif."""
    semua = TugasAkhir.objects.filter(mahasiswa=user)
    return semua.filter(status=TugasAkhir.Status.AKTIF).first() or semua.order_by("-id").first()


def _penghalang(status_ta, item):
    if status_ta != TugasAkhir.Status.AKTIF:
        return "nonaktif"
    if item.diverifikasi_pada:
        return "diverifikasi"
    if item.terkunci:
        return "terkunci"
    return None


def pilihan_milestone(ta):
    """Daftar milestone untuk form unggah, dengan alasan bila belum dapat menerima unggahan."""
    hasil = []
    for item in timeline_ta(ta).items:
        kode = _penghalang(ta.status, item)
        hasil.append(
            {
                "id": item.id,
                "urutan": item.urutan,
                "nama": item.nama,
                "dapat_unggah": kode is None,
                "alasan": _PENGHALANG[kode][0] if kode else "",
            }
        )
    return hasil


def riwayat_queryset(ta, milestone_id=None):
    review_terbit = Review.objects.filter(status=Review.Status.TERBIT).select_related("pemberi").order_by("-diterbitkan_pada", "-id")
    qs = (
        DokumenVersi.objects.select_related("dokumen__milestone")
        .prefetch_related(Prefetch("reviews", queryset=review_terbit, to_attr="reviews_terbit"))
        .filter(dokumen__milestone__tugas_akhir=ta)
    )
    if milestone_id:
        qs = qs.filter(dokumen__milestone_id=milestone_id)
    return qs


def unggah_dokumen(*, tugas_akhir, milestone_id, berkas, catatan=""):
    """Membuat versi baru. BerkasError bila berkas tidak valid, UnggahError bila aturan dilanggar."""
    hasil = validasi_berkas(berkas)  # di luar transaksi: tidak menahan kunci saat membaca berkas
    versi = None
    try:
        with transaction.atomic():
            daftar = list(
                Milestone.objects.select_for_update().filter(tugas_akhir=tugas_akhir).order_by("urutan")
            )
            milestone = next((m for m in daftar if m.pk == milestone_id), None)
            if milestone is None:
                raise Http404
            item = next(i for i in bangun_timeline(daftar).items if i.id == milestone.pk)
            kode = _penghalang(tugas_akhir.status, item)
            if kode:
                raise UnggahError(_PENGHALANG[kode][1])

            dokumen, _ = Dokumen.objects.get_or_create(milestone=milestone)
            terakhir = dokumen.versi.aggregate(n=Max("nomor_versi"))["n"] or 0
            versi = DokumenVersi(
                dokumen=dokumen,
                nomor_versi=terakhir + 1,
                berkas=berkas,
                nama_asli=hasil.nama_asli,
                halaman=hasil.halaman,
                ukuran=hasil.ukuran,
                catatan=catatan,
            )
            versi.save()  # menulis berkas ke storage dengan nama uuid

            penerima = Penugasan.objects.filter(
                tugas_akhir=tugas_akhir, peran__in=[Penugasan.Peran.UTAMA, Penugasan.Peran.PENDAMPING]
            ).select_related("dosen")
            for p in penerima:
                notify(
                    p.dosen,
                    Notifikasi.Jenis.DOKUMEN_BARU,
                    "Dokumen baru menunggu review",
                    f"{tugas_akhir.mahasiswa.nama_lengkap} mengunggah {milestone.nama} (versi {versi.nomor_versi}).",
                    f"{TAUTAN_DOSEN}/{versi.pk}",
                )
    except Exception:
        if versi is not None and versi.berkas.name:  # transaksi dibatalkan: jangan tinggalkan berkas yatim
            versi.berkas.storage.delete(versi.berkas.name)
        raise
    return versi


# --- Akses dan tautan unduh (BR-09) ---


def versi_terjangkau(user):
    """Versi yang boleh diakses pengguna; di luar itu dianggap tidak ada (404)."""
    qs = DokumenVersi.objects.select_related("dokumen__milestone__tugas_akhir")
    if user.role == Role.MAHASISWA:
        return qs.filter(dokumen__milestone__tugas_akhir__mahasiswa=user)
    if user.role == Role.DOSEN:
        return qs.filter(dokumen__milestone__tugas_akhir__penugasan__dosen=user)
    return qs.none()


def buat_token_unduh(user, versi):
    return _penandatangan.sign(f"{versi.pk}:{user.pk}")


def periksa_token_unduh(token, user, versi):
    try:
        nilai = _penandatangan.unsign(token or "", max_age=settings.UNDUH_TOKEN_MAX_AGE)
    except SignatureExpired:
        raise TokenKedaluwarsa from None
    except BadSignature:
        raise TokenTidakValid from None
    if nilai != f"{versi.pk}:{user.pk}":
        raise TokenTidakValid


def url_unduh(user, versi):
    return f"/api/v1/berkas/{versi.pk}/unduh/?" + urlencode({"token": buat_token_unduh(user, versi)})


def url_pratinjau(user, versi):
    """URL pratinjau privat dengan token yang terikat pada pengguna dan versi."""
    return f"/api/v1/berkas/{versi.pk}/pratinjau/?" + urlencode(
        {"token": buat_token_unduh(user, versi)}
    )
