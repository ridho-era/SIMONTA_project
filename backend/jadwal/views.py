from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDosen, IsMahasiswa

from .serializers import (
    BimbinganItemSerializer,
    BimbinganRequestSerializer,
    JadwalMahasiswaResponseSerializer,
    PermohonanDosenResponseSerializer,
    RescheduleSerializer,
    SetujuiSerializer,
    TolakSerializer,
    UsulkanWaktuSerializer,
)
from .services import (
    JadwalError,
    _ambil_milik_dosen,
    buat_permohonan,
    data_jadwal_mahasiswa,
    permohonan_masuk_dosen,
    payload_bimbingan,
    reschedule_mahasiswa,
    setujui_permohonan,
    tolak_permohonan,
    usulkan_waktu_lain,
)


def _respons_konflik(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)


class MahasiswaJadwalView(APIView):
    permission_classes = [IsMahasiswa]

    @extend_schema(summary="Jadwal mendatang, riwayat, dan dosen tujuan mahasiswa", responses=JadwalMahasiswaResponseSerializer)
    def get(self, request):
        return Response(JadwalMahasiswaResponseSerializer(data_jadwal_mahasiswa(request.user)).data)

    @extend_schema(summary="Ajukan jadwal bimbingan", request=BimbinganRequestSerializer, responses={201: BimbinganItemSerializer, 409: None})
    def post(self, request):
        serializer = BimbinganRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = buat_permohonan(mahasiswa=request.user, **serializer.validated_data)
        except Http404:
            raise
        except JadwalError as exc:
            return _respons_konflik(exc)
        return Response(BimbinganItemSerializer(payload_bimbingan(item)).data, status=status.HTTP_201_CREATED)


class RescheduleMahasiswaView(APIView):
    permission_classes = [IsMahasiswa]

    @extend_schema(summary="Ajukan perubahan waktu yang menautkan jadwal sebelumnya", request=RescheduleSerializer, responses={201: BimbinganItemSerializer, 409: None})
    def post(self, request, pk):
        serializer = RescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = reschedule_mahasiswa(mahasiswa=request.user, bimbingan_id=pk, **serializer.validated_data)
        except Http404:
            raise
        except JadwalError as exc:
            return _respons_konflik(exc)
        return Response(BimbinganItemSerializer(payload_bimbingan(item)).data, status=status.HTTP_201_CREATED)


class PermohonanMasukDosenView(APIView):
    permission_classes = [IsDosen]

    @extend_schema(summary="Daftar permohonan jadwal yang ditujukan kepada dosen", responses=PermohonanDosenResponseSerializer)
    def get(self, request):
        return Response(PermohonanDosenResponseSerializer(permohonan_masuk_dosen(request.user)).data)


class _AksiJadwalDosenView(APIView):
    permission_classes = [IsDosen]

    def ambil(self, request, pk):
        # Relasi dosen dan TA diperiksa di query; pihak lain selalu mendapat 404 (BR-09).
        return _ambil_milik_dosen(request.user, pk)


class SetujuiJadwalView(_AksiJadwalDosenView):
    @extend_schema(summary="Setujui permohonan jadwal", request=SetujuiSerializer, responses={200: BimbinganItemSerializer, 409: None})
    def post(self, request, pk):
        self.ambil(request, pk)
        serializer = SetujuiSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = setujui_permohonan(dosen=request.user, bimbingan_id=pk, **serializer.validated_data)
        except Http404:
            raise
        except JadwalError as exc:
            return _respons_konflik(exc)
        return Response(BimbinganItemSerializer(payload_bimbingan(item)).data)


class TolakJadwalView(_AksiJadwalDosenView):
    @extend_schema(summary="Tolak permohonan jadwal dengan alasan", request=TolakSerializer, responses={200: BimbinganItemSerializer, 409: None})
    def post(self, request, pk):
        self.ambil(request, pk)
        serializer = TolakSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = tolak_permohonan(dosen=request.user, bimbingan_id=pk, **serializer.validated_data)
        except Http404:
            raise
        except JadwalError as exc:
            return _respons_konflik(exc)
        return Response(BimbinganItemSerializer(payload_bimbingan(item)).data)


class UsulkanWaktuJadwalView(_AksiJadwalDosenView):
    @extend_schema(summary="Usulkan waktu bimbingan lain", request=UsulkanWaktuSerializer, responses={200: BimbinganItemSerializer, 409: None})
    def post(self, request, pk):
        self.ambil(request, pk)
        serializer = UsulkanWaktuSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = usulkan_waktu_lain(dosen=request.user, bimbingan_id=pk, **serializer.validated_data)
        except Http404:
            raise
        except JadwalError as exc:
            return _respons_konflik(exc)
        return Response(BimbinganItemSerializer(payload_bimbingan(item)).data)
