import os

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDosen, IsMahasiswa
from milestone.serializers import DetailSerializer

from .models import Pesan
from .serializers import (
    KirimPesanSerializer,
    PesanItemSerializer,
    PercakapanListSerializer,
    ThreadSerializer,
)
from .services import (
    daftar_percakapan,
    dokumen_tersedia,
    kirim_pesan,
    peserta_lawan,
    pesan_thread,
    percakapan_terjangkau,
    periksa_token_lampiran,
    tandai_dibaca,
)
from .validators import LampiranPesanError


AKSES_CHAT = [IsMahasiswa | IsDosen]
TIPE_ISI = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


class DaftarPercakapanView(APIView):
    permission_classes = AKSES_CHAT

    @extend_schema(
        summary="Daftar percakapan sesuai penugasan",
        parameters=[OpenApiParameter("q", str, required=False, description="Cari nama, NPM/NIP, atau judul TA")],
        responses=PercakapanListSerializer(many=True),
    )
    def get(self, request):
        hasil = daftar_percakapan(request.user, request.query_params.get("q", ""))
        return Response(PercakapanListSerializer(hasil, many=True, context={"request": request}).data)


class ThreadPesanView(APIView):
    permission_classes = AKSES_CHAT

    @extend_schema(
        summary="Ambil pesan dalam percakapan; gunakan after untuk polling inkremental",
        parameters=[OpenApiParameter("after", int, required=False, description="ID pesan terakhir yang sudah diterima")],
        responses={200: ThreadSerializer},
    )
    def get(self, request, pk):
        percakapan = get_object_or_404(percakapan_terjangkau(request.user), pk=pk)
        raw_after = request.query_params.get("after")
        after = None
        if raw_after not in (None, ""):
            try:
                after = int(raw_after)
                if after < 0:
                    raise ValueError
            except (TypeError, ValueError):
                return Response({"after": ["Parameter after harus berupa ID pesan positif."]}, status=400)
        lawan = peserta_lawan(percakapan, request.user)
        peran = percakapan.tugas_akhir.penugasan.filter(dosen=percakapan.dosen).first()
        data_percakapan = {
            "id": percakapan.pk,
            "tugas_akhir": {"id": percakapan.tugas_akhir_id, "judul": percakapan.tugas_akhir.judul},
            "lawan_bicara": {
                "id": lawan.pk,
                "identifier": lawan.identifier,
                "nama_lengkap": lawan.nama_lengkap,
                "role": lawan.role,
                "peran": peran.peran if request.user.role == "mahasiswa" and peran else "",
                "peran_label": peran.get_peran_display() if request.user.role == "mahasiswa" and peran else "",
            },
        }
        hasil = pesan_thread(percakapan, after=after)
        status_dibaca = list(
            Pesan.objects.filter(
                percakapan=percakapan, pengirim=request.user, dibaca_pada__isnull=False
            ).order_by("-pk").values("id", "dibaca_pada")[:100]
        )
        return Response({
            "percakapan": data_percakapan,
            "dokumen_tersedia": dokumen_tersedia(percakapan),
            "pesan": PesanItemSerializer(hasil, many=True, context={"request": request}).data,
            "pesan_dibaca": status_dibaca,
        })


class KirimPesanView(APIView):
    permission_classes = AKSES_CHAT
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        summary="Kirim pesan teks, lampiran, atau konteks dokumen",
        request=KirimPesanSerializer,
        responses={201: PesanItemSerializer, 400: DetailSerializer},
    )
    def post(self, request, pk):
        percakapan = get_object_or_404(percakapan_terjangkau(request.user), pk=pk)
        serializer = KirimPesanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            pesan = kirim_pesan(
                percakapan=percakapan,
                pengirim=request.user,
                isi=data.get("isi", ""),
                lampiran=data.get("lampiran"),
                dokumen_versi_id=data.get("dokumen_versi"),
            )
        except LampiranPesanError as exc:
            return Response({"lampiran": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            PesanItemSerializer(pesan, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class TandaiDibacaView(APIView):
    permission_classes = AKSES_CHAT

    @extend_schema(summary="Tandai pesan masuk sebagai sudah dibaca", request=None)
    def post(self, request, pk):
        percakapan = get_object_or_404(percakapan_terjangkau(request.user), pk=pk)
        jumlah, dibaca_pada = tandai_dibaca(percakapan, request.user)
        return Response({"ditandai": jumlah, "dibaca_pada": dibaca_pada})


class UnduhLampiranPesanView(APIView):
    permission_classes = AKSES_CHAT

    @extend_schema(
        summary="Unduh lampiran pesan privat",
        parameters=[OpenApiParameter("token", str, required=True)],
        responses={(200, "application/octet-stream"): bytes, 410: DetailSerializer},
    )
    def get(self, request, pk):
        pesan = get_object_or_404(
            Pesan.objects.select_related("percakapan", "pengirim"),
            pk=pk,
            percakapan__in=percakapan_terjangkau(request.user),
        )
        if not pesan.lampiran:
            raise Http404
        try:
            periksa_token_lampiran(request.query_params.get("token", ""), request.user, pesan)
        except TimeoutError:
            return Response({"detail": "Tautan lampiran kedaluwarsa. Muat ulang percakapan."}, status=410)
        except PermissionError:
            return Response({"detail": "Tautan lampiran tidak valid."}, status=403)
        try:
            handle = pesan.lampiran.open("rb")
        except (FileNotFoundError, ValueError):
            raise Http404 from None
        ekstensi = os.path.splitext(pesan.lampiran.name)[1].lower()
        respons = FileResponse(
            handle,
            as_attachment=True,
            filename=pesan.nama_lampiran or os.path.basename(pesan.lampiran.name),
            content_type=TIPE_ISI.get(ekstensi, "application/octet-stream"),
        )
        respons["X-Content-Type-Options"] = "nosniff"
        respons["Cache-Control"] = "private, no-store"
        return respons
