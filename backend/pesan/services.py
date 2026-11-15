from urllib.parse import urlencode

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q
from django.http import Http404
from django.utils import timezone

from accounts.models import Role
from akademik.models import Penugasan
from dokumen.models import DokumenVersi
from notifikasi.models import Notifikasi
from notifikasi.services import notify

from .models import Percakapan, Pesan
from .validators import validasi_lampiran

_penandatangan = TimestampSigner(salt="pesan.lampiran")


class AksesPercakapanError(Exception):
    pass


class PesanTidakValid(ValueError):
    pass


def percakapan_terjangkau(user):
    """Queryset percakapan yang hanya memuat pasangan pengguna bersangkutan."""
    qs = Percakapan.objects.select_related("tugas_akhir__mahasiswa", "dosen", "tugas_akhir")
    if user.role == Role.MAHASISWA:
        return qs.filter(
            tugas_akhir__mahasiswa=user,
            tugas_akhir__penugasan__dosen_id=F("dosen_id"),
        )
    if user.role == Role.DOSEN:
        return qs.filter(dosen=user, tugas_akhir__penugasan__dosen=user)
    return qs.none()


def peserta_lawan(percakapan, user):
    lawan = percakapan.lawan_bicara(user)
    if lawan is None:
        raise Http404
    return lawan


def pastikan_percakapan_penugasan(user):
    """Materialisasikan satu thread per pasangan dari penugasan yang sah.

    Daftar kontak F-08/F-15 perlu tersedia walaupun pasangan belum pernah mengirim pesan.
    Unique constraint di database menjaga agar GET berulang tidak membuat thread ganda.
    """
    if user.role == Role.MAHASISWA:
        penugasan = Penugasan.objects.filter(
            tugas_akhir__mahasiswa=user
        ).values_list("tugas_akhir_id", "dosen_id")
    elif user.role == Role.DOSEN:
        penugasan = Penugasan.objects.filter(dosen=user).values_list(
            "tugas_akhir_id", "dosen_id"
        )
    else:
        return
    data = [Percakapan(tugas_akhir_id=ta_id, dosen_id=dosen_id) for ta_id, dosen_id in penugasan]
    if data:
        Percakapan.objects.bulk_create(data, ignore_conflicts=True)


def daftar_percakapan(user, pencarian=""):
    pastikan_percakapan_penugasan(user)
    qs = percakapan_terjangkau(user).annotate(
        jumlah_belum_dibaca=Count(
            "pesan",
            filter=Q(pesan__dibaca_pada__isnull=True) & ~Q(pesan__pengirim=user),
        )
    ).prefetch_related(
        Prefetch(
            "pesan",
            queryset=Pesan.objects.select_related("pengirim").order_by("-dibuat_pada", "-id")[:1],
            to_attr="pesan_terakhir_list",
        )
    )
    kata = (pencarian or "").strip()
    if kata:
        qs = qs.filter(
            Q(tugas_akhir__judul__icontains=kata)
            | Q(tugas_akhir__mahasiswa__nama_lengkap__icontains=kata)
            | Q(tugas_akhir__mahasiswa__identifier__icontains=kata)
            | Q(dosen__nama_lengkap__icontains=kata)
            | Q(dosen__identifier__icontains=kata)
        )
    hasil = list(qs.order_by("-diubah_pada", "-id"))
    for item in hasil:
        item.pesan_terakhir = item.pesan_terakhir_list[0] if item.pesan_terakhir_list else None
    return hasil


def pesan_thread(percakapan, after=None, batas=100):
    qs = Pesan.objects.filter(percakapan=percakapan).select_related(
        "pengirim", "dokumen_versi__dokumen__milestone"
    )
    if after is not None:
        return qs.filter(pk__gt=after).order_by("pk")
    ids = list(qs.order_by("-pk").values_list("pk", flat=True)[:batas])
    return qs.filter(pk__in=ids).order_by("pk")


def dokumen_tersedia(percakapan):
    qs = DokumenVersi.objects.filter(
        dokumen__milestone__tugas_akhir=percakapan.tugas_akhir
    ).select_related("dokumen__milestone").order_by("-diunggah_pada", "-id")[:50]
    return [
        {
            "id": versi.pk,
            "nama_asli": versi.nama_asli,
            "nomor_versi": versi.nomor_versi,
            "milestone": versi.dokumen.milestone.nama,
        }
        for versi in qs
    ]


def kirim_pesan(*, percakapan, pengirim, isi="", lampiran=None, dokumen_versi_id=None):
    isi = (isi or "").strip()
    if not isi and lampiran is None and dokumen_versi_id is None:
        raise PesanTidakValid("Isi pesan, lampiran, atau konteks dokumen harus diisi.")
    if len(isi) > 10000:
        raise PesanTidakValid("Pesan maksimal 10.000 karakter.")
    if not percakapan.peserta(pengirim):
        raise Http404

    hasil_lampiran = validasi_lampiran(lampiran) if lampiran is not None else None
    versi = None
    if dokumen_versi_id is not None:
        versi = DokumenVersi.objects.select_related("dokumen__milestone").filter(
            pk=dokumen_versi_id,
            dokumen__milestone__tugas_akhir=percakapan.tugas_akhir,
        ).first()
        if versi is None:
            raise PesanTidakValid("Dokumen yang dipilih bukan milik tugas akhir percakapan ini.")

    pesan = None
    try:
        with transaction.atomic():
            pesan = Pesan(
                percakapan=percakapan,
                pengirim=pengirim,
                isi=isi,
                nama_lampiran=hasil_lampiran.nama_asli if hasil_lampiran else "",
                dokumen_versi=versi,
            )
            if lampiran is not None:
                pesan.lampiran = lampiran
            pesan.save()
            Percakapan.objects.filter(pk=percakapan.pk).update(diubah_pada=timezone.now())
            penerima = peserta_lawan(percakapan, pengirim)
            tautan = "/dosen/chat" if penerima.role == Role.DOSEN else "/mahasiswa/pesan"
            ringkas = isi[:180] if isi else (f"Mengirim lampiran: {hasil_lampiran.nama_asli}" if hasil_lampiran else "Membagikan dokumen")
            notify(
                penerima,
                Notifikasi.Jenis.PESAN_BARU,
                "Pesan baru dari " + pengirim.nama_lengkap,
                ringkas,
                tautan,
            )
    except Exception:
        if pesan is not None and pesan.lampiran.name:
            pesan.lampiran.storage.delete(pesan.lampiran.name)
        raise
    return pesan


def tandai_dibaca(percakapan, pembaca):
    peserta_lawan(percakapan, pembaca)
    sekarang = timezone.now()
    jumlah = Pesan.objects.filter(
        percakapan=percakapan,
        dibaca_pada__isnull=True,
    ).exclude(pengirim=pembaca).update(dibaca_pada=sekarang)
    return jumlah, sekarang


def buat_token_lampiran(user, pesan):
    return _penandatangan.sign(f"{pesan.pk}:{user.pk}")


def periksa_token_lampiran(token, user, pesan):
    try:
        nilai = _penandatangan.unsign(
            token or "", max_age=settings.UNDUH_TOKEN_MAX_AGE
        )
    except SignatureExpired:
        raise TimeoutError from None
    except BadSignature:
        raise PermissionError from None
    if nilai != f"{pesan.pk}:{user.pk}":
        raise PermissionError


def url_lampiran(user, pesan):
    return "/api/v1/pesan/lampiran/" + str(pesan.pk) + "/unduh/?" + urlencode(
        {"token": buat_token_lampiran(user, pesan)}
    )
