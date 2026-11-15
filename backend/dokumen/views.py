import os

from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDosen, IsMahasiswa
from milestone.serializers import DetailSerializer

from .serializers import DokumenSayaSerializer, UnggahSerializer, VersiSerializer
from .services import (
    TokenKedaluwarsa,
    TokenTidakValid,
    UnggahError,
    periksa_token_unduh,
    pilihan_milestone,
    riwayat_queryset,
    ta_saya,
    unggah_dokumen,
    versi_terjangkau,
)
from .validators import EKSTENSI, MAKS_UKURAN, BerkasError

BARIS_PER_HALAMAN = 20
TIPE_ISI = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
BELUM_ADA_TA = "Tugas akhir Anda belum didaftarkan. Hubungi admin Prodi."


class DokumenSayaView(APIView):
    permission_classes = [IsMahasiswa]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Opsi unggah dan riwayat berkas milik mahasiswa",
        parameters=[
            OpenApiParameter("milestone", int, required=False, description="Saring riwayat per milestone"),
            OpenApiParameter("halaman", int, required=False),
        ],
        responses=DokumenSayaSerializer,
    )
    def get(self, request):
        ta = ta_saya(request.user)
        batas = {"ukuran_maks_mb": MAKS_UKURAN // (1024 * 1024), "ekstensi": list(EKSTENSI)}
        if ta is None:
            payload = {
                "tugas_akhir": None,
                "milestone": [],
                "riwayat": {"jumlah": 0, "halaman": 1, "total_halaman": 1, "hasil": []},
                "batas": batas,
            }
        else:
            try:
                milestone_id = int(request.query_params.get("milestone", ""))
            except ValueError:
                milestone_id = None
            paginator = Paginator(riwayat_queryset(ta, milestone_id), BARIS_PER_HALAMAN)
            halaman = paginator.get_page(request.query_params.get("halaman"))
            payload = {
                "tugas_akhir": {"id": ta.pk, "judul": ta.judul},
                "milestone": pilihan_milestone(ta),
                "riwayat": {
                    "jumlah": paginator.count,
                    "halaman": halaman.number,
                    "total_halaman": paginator.num_pages,
                    "hasil": list(halaman.object_list),
                },
                "batas": batas,
            }
        return Response(DokumenSayaSerializer(payload, context={"request": request}).data)

    @extend_schema(
        summary="Unggah draf milestone (multipart)",
        request={"multipart/form-data": UnggahSerializer},
        responses={201: VersiSerializer, 409: DetailSerializer},
    )
    def post(self, request):
        ta = ta_saya(request.user)
        if ta is None:
            return Response({"detail": BELUM_ADA_TA}, status=status.HTTP_409_CONFLICT)
        serializer = UnggahSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            versi = unggah_dokumen(
                tugas_akhir=ta,
                milestone_id=data["milestone"],
                berkas=data["berkas"],
                catatan=data["catatan"].strip(),
            )
        except BerkasError as exc:
            return Response({"berkas": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        except UnggahError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(VersiSerializer(versi, context={"request": request}).data, status=status.HTTP_201_CREATED)


class PratinjauBerkasView(APIView):
    """Menyajikan berkas secara inline untuk viewer PDF/DOCX, tetap privat (BR-09)."""

    permission_classes = [IsMahasiswa | IsDosen]

    @extend_schema(
        summary="Pratinjau berkas privat (PDF atau DOCX)",
        parameters=[OpenApiParameter("token", str, required=True)],
        responses={(200, "application/octet-stream"): bytes, 410: DetailSerializer},
    )
    def get(self, request, pk):
        versi = get_object_or_404(versi_terjangkau(request.user), pk=pk)
        try:
            periksa_token_unduh(request.query_params.get("token", ""), request.user, versi)
        except TokenKedaluwarsa:
            return Response(
                {"detail": "Tautan pratinjau kedaluwarsa. Muat ulang halaman untuk mendapat tautan baru."},
                status=status.HTTP_410_GONE,
            )
        except TokenTidakValid:
            return Response({"detail": "Tautan pratinjau tidak valid."}, status=status.HTTP_403_FORBIDDEN)

        try:
            handle = versi.berkas.open("rb")
        except (FileNotFoundError, ValueError):
            raise Http404 from None

        ekstensi = os.path.splitext(versi.berkas.name)[1].lower()
        respons = FileResponse(
            handle,
            as_attachment=False,
            filename=versi.nama_asli,
            content_type=TIPE_ISI.get(ekstensi, "application/octet-stream"),
        )
        respons["X-Content-Type-Options"] = "nosniff"
        respons["Cache-Control"] = "private, no-store"
        return respons


class UnduhBerkasView(APIView):
    permission_classes = [IsMahasiswa | IsDosen]

    @extend_schema(
        summary="Unduh berkas (butuh sesi, hak akses, dan token bertanda waktu)",
        parameters=[OpenApiParameter("token", str, required=True)],
        responses={(200, "application/octet-stream"): bytes, 410: DetailSerializer},
    )
    def get(self, request, pk):
        versi = get_object_or_404(versi_terjangkau(request.user), pk=pk)  # tanpa hak akses: 404
        try:
            periksa_token_unduh(request.query_params.get("token", ""), request.user, versi)
        except TokenKedaluwarsa:
            return Response(
                {"detail": "Tautan unduhan kedaluwarsa. Muat ulang halaman untuk mendapat tautan baru."},
                status=status.HTTP_410_GONE,
            )
        except TokenTidakValid:
            return Response({"detail": "Tautan unduhan tidak valid."}, status=status.HTTP_403_FORBIDDEN)
        try:
            handle = versi.berkas.open("rb")
        except (FileNotFoundError, ValueError):
            raise Http404 from None
        ekstensi = os.path.splitext(versi.berkas.name)[1].lower()
        respons = FileResponse(
            handle,
            as_attachment=True,
            filename=versi.nama_asli,
            content_type=TIPE_ISI.get(ekstensi, "application/octet-stream"),
        )
        respons["X-Content-Type-Options"] = "nosniff"
        respons["Cache-Control"] = "private, no-store"
        return respons