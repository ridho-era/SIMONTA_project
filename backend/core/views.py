import logging

from django.db import connection
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDosen, IsMahasiswa
from .models import HalamanBantuan
from .serializers import HalamanBantuanSerializer

logger = logging.getLogger(__name__)


class DatabaseStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok", "error"])


class HealthSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok", "degraded"])
    database = DatabaseStatusSerializer()
    timestamp = serializers.DateTimeField()


class HealthView(APIView):
    """Cek kesehatan aplikasi dan koneksi database. Publik, tanpa data pengguna."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Cek kesehatan aplikasi",
        responses={200: HealthSerializer, 503: HealthSerializer},
        auth=[],
    )
    def get(self, request):
        database_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:  # detail galat hanya ke log, tidak ke respons publik
            logger.exception("Cek koneksi database gagal")
            database_ok = False

        payload = {
            "status": "ok" if database_ok else "degraded",
            "database": {"status": "ok" if database_ok else "error"},
            "timestamp": timezone.now().isoformat(),
        }
        http_status = (
            status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(payload, status=http_status)

class PusatBantuanView(APIView):
    permission_classes = [IsMahasiswa | IsDosen]

    @extend_schema(summary="Daftar halaman Pusat Bantuan", responses=HalamanBantuanSerializer(many=True))
    def get(self, request):
        halaman = HalamanBantuan.objects.filter(aktif=True).order_by("urutan", "judul", "id")
        return Response(HalamanBantuanSerializer(halaman, many=True).data)
