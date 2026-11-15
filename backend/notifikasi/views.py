from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role

from .models import Notifikasi
from .serializers import (
    NotifikasiSerializer,
    PengaturanNotifikasiSerializer,
    PratinjauPengingatItemSerializer,
)
from .services import (
    daftar_milestone_pratinjau,
    pengaturan_untuk,
    sinkronkan_pengingat_pengguna,
)


def _pastikan_portal(request):
    if request.user.role not in {Role.MAHASISWA, Role.DOSEN}:
        return Response({"detail": "Menu ini hanya tersedia untuk mahasiswa dan dosen."}, status=403)
    return None


class DaftarNotifikasiView(APIView):
    @extend_schema(summary="Daftar semua notifikasi atau hanya yang belum dibaca")
    def get(self, request):
        tolak = _pastikan_portal(request)
        if tolak:
            return tolak
        mode = request.query_params.get("status", "semua")
        if mode not in {"semua", "belum_dibaca"}:
            return Response({"detail": "Parameter status harus semua atau belum_dibaca."}, status=400)
        semua = Notifikasi.objects.filter(user=request.user, tampil_di_aplikasi=True)
        belum = semua.filter(dibaca_pada__isnull=True).count()
        hasil = semua
        if mode == "belum_dibaca":
            hasil = hasil.filter(dibaca_pada__isnull=True)
        hasil = hasil[:100]
        return Response(
            {
                "jumlah": len(hasil),
                "jumlah_belum_dibaca": belum,
                "hasil": NotifikasiSerializer(hasil, many=True).data,
            }
        )


class JumlahBelumDibacaView(APIView):
    @extend_schema(summary="Jumlah notifikasi yang belum dibaca untuk badge")
    def get(self, request):
        tolak = _pastikan_portal(request)
        if tolak:
            return tolak
        jumlah = Notifikasi.objects.filter(user=request.user, tampil_di_aplikasi=True, dibaca_pada__isnull=True).count()
        return Response({"jumlah_belum_dibaca": jumlah})


class TandaiNotifikasiDibacaView(APIView):
    @extend_schema(summary="Tandai satu notifikasi milik pengguna sebagai dibaca")
    def post(self, request, pk):
        tolak = _pastikan_portal(request)
        if tolak:
            return tolak
        item = get_object_or_404(Notifikasi, pk=pk, user=request.user, tampil_di_aplikasi=True)
        if item.dibaca_pada is None:
            item.dibaca_pada = timezone.now()
            item.save(update_fields=["dibaca_pada"])
        return Response(NotifikasiSerializer(item).data)


class TandaiSemuaDibacaView(APIView):
    @extend_schema(summary="Tandai seluruh notifikasi pengguna sebagai dibaca")
    def post(self, request):
        tolak = _pastikan_portal(request)
        if tolak:
            return tolak
        jumlah = Notifikasi.objects.filter(
            user=request.user, tampil_di_aplikasi=True, dibaca_pada__isnull=True
        ).update(dibaca_pada=timezone.now())
        return Response({"jumlah_diperbarui": jumlah})


class PengaturanNotifikasiView(APIView):
    @extend_schema(summary="Ambil atau simpan pengaturan notifikasi")
    def get(self, request):
        tolak = _pastikan_portal(request)
        if tolak:
            return tolak
        return Response(PengaturanNotifikasiSerializer(pengaturan_untuk(request.user)).data)

    def patch(self, request):
        tolak = _pastikan_portal(request)
        if tolak:
            return tolak
        obj = pengaturan_untuk(request.user)
        serializer = PengaturanNotifikasiSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        sinkronkan_pengingat_pengguna(request.user)
        return Response(serializer.data)


class PulihkanDefaultNotifikasiView(APIView):
    @extend_schema(summary="Pulihkan pengaturan notifikasi ke nilai default")
    def post(self, request):
        tolak = _pastikan_portal(request)
        if tolak:
            return tolak
        obj = pengaturan_untuk(request.user)
        for field, value in {
            "pengingat_aktif": True,
            "h_minus_7": True,
            "h_minus_3": True,
            "h_minus_1": True,
            "kanal_aplikasi": True,
            "kanal_email": False,
            "ringkasan_mingguan": False,
            "dokumen_feedback_aktif": True,
            "jadwal_bimbingan_aktif": True,
            "jam_kirim": "08:00:00",
            "zona_waktu": "Asia/Jakarta",
        }.items():
            setattr(obj, field, value)
        obj.save()
        sinkronkan_pengingat_pengguna(request.user)
        return Response(PengaturanNotifikasiSerializer(obj).data)


class PratinjauPengingatView(APIView):
    @extend_schema(summary="Pratinjau jadwal H-7/H-3/H-1 dari milestone aktif")
    def get(self, request):
        tolak = _pastikan_portal(request)
        if tolak:
            return tolak
        pengaturan = pengaturan_untuk(request.user)
        hasil = daftar_milestone_pratinjau(request.user, pengaturan)
        return Response(
            {
                "aktif": pengaturan.pengingat_aktif,
                "zona_waktu": pengaturan.zona_waktu,
                "jam_kirim": pengaturan.jam_kirim,
                "jumlah": len(hasil),
                "hasil": PratinjauPengingatItemSerializer(hasil, many=True).data,
            }
        )
