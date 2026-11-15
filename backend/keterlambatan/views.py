from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role
from accounts.permissions import IsMahasiswa
from akademik.models import JenisSanksi, Penugasan, TugasAkhir
from dokumen.services import ta_saya

from .models import CatatanKeterlambatan, Keberatan, SanksiTercatat
from .permissions import IsDosenAtauAdmin
from .serializers import (
    CatatanAdministrasiSerializer,
    KeputusanCatatanSerializer,
    KeputusanKeberatanSerializer,
    PengajuanKeberatanSerializer,
)
from .services import (
    batalkan_catatan,
    buat_catatan_administrasi,
    konfirmasi_catatan,
    hitung_denda,
    keberatan_boleh_diakses,
    putuskan_keberatan,
    ringkasan_denda_mahasiswa,
    simpan_atau_ajukan_keberatan,
)
from .validators import BuktiKeberatanError, validasi_bukti


def _status_label(catatan):
    return catatan.get_status_penilaian_display()


def _catatan_payload(catatan, *, include_detail=False):
    perhitungan = hitung_denda(
        tenggat=catatan.tenggat,
        realisasi=catatan.realisasi,
        tarif=catatan.tarif,
        toleransi=catatan.toleransi_hari,
        batas=catatan.batas_per_catatan,
    )
    try:
        keberatan = catatan.keberatan
    except Keberatan.DoesNotExist:
        keberatan = None

    data = {
        "id": catatan.pk,
        "tugas_akhir_id": catatan.tugas_akhir_id,
        "mahasiswa": {
            "id": catatan.tugas_akhir.mahasiswa_id,
            "identifier": catatan.tugas_akhir.mahasiswa.identifier,
            "nama_lengkap": catatan.tugas_akhir.mahasiswa.nama_lengkap,
        },
        "jenis": catatan.jenis,
        "jenis_label": catatan.get_jenis_display(),
        "nama_dokumen": catatan.nama_dokumen or (catatan.review.versi.nama_asli if catatan.review_id else ""),
        "milestone": catatan.milestone.nama if catatan.milestone_id else "",
        "tenggat": catatan.tenggat.isoformat(),
        "realisasi": catatan.realisasi.isoformat() if catatan.realisasi else None,
        "hari_terlambat": perhitungan["hari_terlambat"],
        "tarif": perhitungan["tarif"],
        "toleransi_hari": perhitungan["toleransi_hari"],
        "hari_dikenai": perhitungan["hari_dikenai"],
        "batas_per_catatan": perhitungan["batas_per_catatan"],
        "subtotal": perhitungan["subtotal"],
        "nominal": perhitungan["nominal"],
        "rumus": perhitungan["rumus"],
        "status_penilaian": catatan.status_penilaian,
        "status_label": _status_label(catatan),
        "label_simulasi": catatan.label_simulasi,
        "catatan_peninjau": catatan.catatan_peninjau,
        "ditinjau_oleh": catatan.ditinjau_oleh.nama_lengkap if catatan.ditinjau_oleh_id else None,
        "ditinjau_pada": catatan.ditinjau_pada.isoformat() if catatan.ditinjau_pada else None,
        "keberatan": _keberatan_payload(keberatan) if keberatan else None,
    }
    if include_detail:
        try:
            sanksi = catatan.sanksi_tercatat
        except SanksiTercatat.DoesNotExist:
            sanksi = None
        data.update({
            "tugas_akhir": {
                "id": catatan.tugas_akhir_id,
                "judul": catatan.tugas_akhir.judul,
                "periode": catatan.tugas_akhir.periode.label,
            },
            "review_id": catatan.review_id,
            "jenis_sanksi": {
                "id": sanksi.jenis_sanksi_id,
                "nama": sanksi.jenis_sanksi.nama,
                "keterangan": sanksi.keterangan,
            } if sanksi else None,
            "pratinjau": perhitungan,
        })
    return data


def _keberatan_payload(keberatan):
    return {
        "id": keberatan.pk,
        "alasan": keberatan.alasan,
        "nama_bukti": keberatan.nama_bukti,
        "ukuran_bukti": keberatan.ukuran_bukti,
        "bukti_url": f"/api/v1/keberatan/{keberatan.pk}/bukti/" if keberatan.bukti else None,
        "status": keberatan.status,
        "status_label": keberatan.get_status_display(),
        "catatan_peninjau": keberatan.catatan_peninjau,
        "diajukan_pada": keberatan.diajukan_pada.isoformat() if keberatan.diajukan_pada else None,
        "ditinjau_pada": keberatan.ditinjau_pada.isoformat() if keberatan.ditinjau_pada else None,
    }


def _ta_untuk_dosen(user):
    if user.role == Role.ADMIN:
        return TugasAkhir.objects.select_related("mahasiswa", "periode").filter(
            status=TugasAkhir.Status.AKTIF
        )
    return TugasAkhir.objects.select_related("mahasiswa", "periode").filter(
        status=TugasAkhir.Status.AKTIF,
        penugasan__dosen=user,
        penugasan__peran=Penugasan.Peran.UTAMA,
    ).distinct()


def _catatan_untuk_dosen(user):
    qs = CatatanKeterlambatan.objects.select_related(
        "tugas_akhir__mahasiswa",
        "tugas_akhir__periode",
        "konfigurasi",
        "milestone",
        "review__versi",
        "ditinjau_oleh",
    ).prefetch_related("keberatan", "sanksi_tercatat__jenis_sanksi")
    if user.role == Role.ADMIN:
        return qs
    return qs.filter(
        tugas_akhir__penugasan__dosen=user,
        tugas_akhir__penugasan__peran=Penugasan.Peran.UTAMA,
    ).distinct()


def _aturan_untuk_tugas_akhir(ta):
    from akademik.models import KonfigurasiDenda

    return [
        {
            "jenis": item.jenis,
            "jenis_label": item.get_jenis_display(),
            "tarif": item.tarif,
            "toleransi_hari": item.toleransi_hari,
            "batas_per_catatan": item.batas_per_catatan,
            "label_simulasi": item.label_simulasi,
        }
        for item in KonfigurasiDenda.objects.filter(periode=ta.periode).order_by("jenis")
    ]


class MahasiswaDendaView(APIView):
    permission_classes = [IsMahasiswa]

    def get(self, request):
        ta = ta_saya(request.user)
        if ta is None:
            return Response({"ringkasan": None, "aturan": [], "hasil": [], "kosong": True})
        catatan_qs = CatatanKeterlambatan.objects.filter(
            tugas_akhir=ta
        ).select_related(
            "tugas_akhir__mahasiswa", "tugas_akhir__periode", "milestone", "review__versi", "ditinjau_oleh"
        ).prefetch_related("keberatan")
        hasil = [_catatan_payload(item) for item in catatan_qs]
        return Response({
            "ringkasan": ringkasan_denda_mahasiswa(ta),
            "aturan": _aturan_untuk_tugas_akhir(ta),
            "hasil": hasil,
            "kosong": len(hasil) == 0,
        })


class MahasiswaKeberatanView(APIView):
    permission_classes = [IsMahasiswa]

    def post(self, request, catatan_id):
        ta = ta_saya(request.user)
        catatan = CatatanKeterlambatan.objects.filter(
            pk=catatan_id,
            tugas_akhir=ta,
        ).select_related("tugas_akhir__mahasiswa").first()
        if catatan is None:
            raise Http404

        serializer = PengajuanKeberatanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        bukti = data.get("bukti")
        hasil_bukti = None
        if bukti is not None:
            try:
                hasil_bukti = validasi_bukti(bukti)
            except BuktiKeberatanError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            keberatan = simpan_atau_ajukan_keberatan(
                catatan=catatan,
                mahasiswa=request.user,
                alasan=data["alasan"],
                bukti=bukti,
                nama_bukti=hasil_bukti.nama_asli if hasil_bukti else "",
                ukuran_bukti=hasil_bukti.ukuran if hasil_bukti else None,
                aksi=data["aksi"],
            )
        except CatatanKeterlambatan.DoesNotExist:
            raise Http404
        except Exception as exc:
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                pesan = exc.messages if hasattr(exc, "messages") else str(exc)
                return Response({"detail": pesan}, status=status.HTTP_400_BAD_REQUEST)
            raise
        return Response(_keberatan_payload(keberatan), status=status.HTTP_200_OK)


class DosenKeterlambatanView(APIView):
    permission_classes = [IsDosenAtauAdmin]

    def get(self, request):
        qs = _catatan_untuk_dosen(request.user)
        cari = (request.query_params.get("q") or "").strip()
        jenis = request.query_params.get("jenis") or ""
        status_filter = request.query_params.get("status") or ""
        if cari:
            from django.db.models import Q

            qs = qs.filter(
                Q(tugas_akhir__mahasiswa__nama_lengkap__icontains=cari)
                | Q(tugas_akhir__mahasiswa__identifier__icontains=cari)
            )
        if jenis:
            pilihan_jenis = {value for value, _label in CatatanKeterlambatan._meta.get_field("jenis").choices}
            if jenis not in pilihan_jenis:
                return Response({"detail": "Filter jenis tidak dikenal."}, status=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(jenis=jenis)
        if status_filter:
            pilihan_status = {value for value, _label in CatatanKeterlambatan.StatusPenilaian.choices}
            if status_filter not in pilihan_status:
                return Response({"detail": "Filter status penilaian tidak dikenal."}, status=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(status_penilaian=status_filter)

        ta_options = [
            {"id": ta.pk, "mahasiswa": ta.mahasiswa.nama_lengkap, "identifier": ta.mahasiswa.identifier, "judul": ta.judul}
            for ta in _ta_untuk_dosen(request.user).order_by("mahasiswa__nama_lengkap", "id")
        ]
        hasil = [_catatan_payload(item, include_detail=True) for item in qs.order_by("-tenggat", "-id")]
        from akademik.models import KonfigurasiDenda

        periode_ids = _ta_untuk_dosen(request.user).values_list("periode_id", flat=True).distinct()
        label_simulasi = KonfigurasiDenda.objects.filter(
            periode_id__in=periode_ids,
            label_simulasi=True,
        ).exists()
        return Response({
            "jumlah": len(hasil),
            "hasil": hasil,
            "ta_options": ta_options,
            "label_simulasi": label_simulasi,
        })


class DosenCatatanAdministrasiView(APIView):
    permission_classes = [IsDosenAtauAdmin]

    def post(self, request):
        serializer = CatatanAdministrasiSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ta = _ta_untuk_dosen(request.user).filter(pk=data["tugas_akhir_id"]).first()
        if ta is None:
            raise Http404
        try:
            catatan = buat_catatan_administrasi(
                tugas_akhir=ta,
                nama_dokumen=data["nama_dokumen"],
                tenggat=data["tenggat"],
                realisasi=data.get("realisasi"),
                aktor=request.user,
            )
        except Exception as exc:
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                pesan = exc.messages if hasattr(exc, "messages") else str(exc)
                return Response({"detail": pesan}, status=status.HTTP_400_BAD_REQUEST)
            raise
        catatan = _catatan_untuk_dosen(request.user).get(pk=catatan.pk)
        return Response(_catatan_payload(catatan, include_detail=True), status=status.HTTP_201_CREATED)


class DosenCatatanDetailView(APIView):
    permission_classes = [IsDosenAtauAdmin]

    def get(self, request, catatan_id):
        catatan = _catatan_untuk_dosen(request.user).filter(pk=catatan_id).first()
        if catatan is None:
            raise Http404
        return Response({
            "catatan": _catatan_payload(catatan, include_detail=True),
            "jenis_sanksi": [
                {"id": item.pk, "nama": item.nama}
                for item in JenisSanksi.objects.filter(aktif=True).order_by("nama")
            ],
        })


class DosenKeputusanCatatanView(APIView):
    permission_classes = [IsDosenAtauAdmin]

    def post(self, request, catatan_id):
        catatan = _catatan_untuk_dosen(request.user).filter(pk=catatan_id).first()
        if catatan is None:
            raise Http404
        serializer = KeputusanCatatanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            if data["aksi"] == "batalkan":
                hasil = batalkan_catatan(
                    catatan=catatan,
                    aktor=request.user,
                    catatan_peninjau=data.get("catatan_peninjau", ""),
                )
            else:
                jenis_sanksi = None
                jenis_sanksi_id = data.get("jenis_sanksi_id")
                if jenis_sanksi_id:
                    jenis_sanksi = JenisSanksi.objects.filter(pk=jenis_sanksi_id, aktif=True).first()
                    if jenis_sanksi is None:
                        return Response({"detail": "Jenis sanksi tidak ditemukan atau tidak aktif."}, status=status.HTTP_400_BAD_REQUEST)
                hasil = konfirmasi_catatan(
                    catatan=catatan,
                    aktor=request.user,
                    catatan_peninjau=data.get("catatan_peninjau", ""),
                    jenis_sanksi=jenis_sanksi,
                )
        except Exception as exc:
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                pesan = exc.messages if hasattr(exc, "messages") else str(exc)
                return Response({"detail": pesan}, status=status.HTTP_400_BAD_REQUEST)
            raise
        hasil = _catatan_untuk_dosen(request.user).get(pk=hasil.pk)
        return Response(_catatan_payload(hasil, include_detail=True))


class DosenKeputusanKeberatanView(APIView):
    permission_classes = [IsDosenAtauAdmin]

    def post(self, request, keberatan_id):
        keberatan = Keberatan.objects.select_related("catatan__tugas_akhir__mahasiswa").filter(pk=keberatan_id).first()
        if keberatan is None or not keberatan_boleh_diakses(request.user, keberatan):
            raise Http404
        serializer = KeputusanKeberatanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            hasil = putuskan_keberatan(
                keberatan=keberatan,
                aktor=request.user,
                aksi=data["aksi"],
                catatan_peninjau=data.get("catatan_peninjau", ""),
            )
        except Exception as exc:
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                pesan = exc.messages if hasattr(exc, "messages") else str(exc)
                return Response({"detail": pesan}, status=status.HTTP_400_BAD_REQUEST)
            raise
        return Response(_keberatan_payload(hasil))


class KeberatanBuktiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, keberatan_id):
        if not request.user.is_active or request.user.must_change_password:
            return Response({"detail": "Akun tidak diizinkan mengakses berkas ini."}, status=status.HTTP_403_FORBIDDEN)
        keberatan = Keberatan.objects.select_related(
            "catatan__tugas_akhir__mahasiswa"
        ).filter(pk=keberatan_id).first()
        if keberatan is None or not keberatan_boleh_diakses(request.user, keberatan) or not keberatan.bukti:
            raise Http404
        nama = keberatan.nama_bukti or "bukti-keberatan"
        ekstensi = nama.lower().rsplit(".", 1)[-1] if "." in nama else "pdf"
        content_type = "application/pdf" if ekstensi == "pdf" else "image/jpeg"
        keberatan.bukti.open("rb")
        return FileResponse(
            keberatan.bukti,
            as_attachment=True,
            filename=nama,
            content_type=content_type,
        )
