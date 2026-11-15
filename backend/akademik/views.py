from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PeriodeAkademik
from .serializers import PeriodeAktifResponseSerializer, PeriodeAktifSerializer


class PeriodeAktifView(APIView):
    """Periode akademik yang sedang aktif. `periode` bernilai null bila belum ada."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Periode akademik aktif", responses=PeriodeAktifResponseSerializer)
    def get(self, request):
        periode = PeriodeAkademik.aktif_sekarang()
        data = PeriodeAktifSerializer(periode).data if periode else None
        return Response({"periode": data})