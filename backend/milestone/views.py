from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDosen, IsMahasiswa
from akademik.models import Penugasan, TugasAkhir

from .models import Milestone
from .serializers import (
    AksiResponseSerializer,
    DetailSerializer,
    TargetSerializer,
    TimelineSerializer,
    VerifikasiSerializer,
)
from .services import MilestoneError, tetapkan_target, timeline_ta, verifikasi


def _payload_timeline(ta):
    if ta is None:
        return {"tugas_akhir": None, "progres": 0, "jumlah_diverifikasi": 0, "tahap_aktif": None, "milestone": []}
    tl = timeline_ta(ta)
    aktif = next((i for i in tl.items if i.tahap_aktif), None)
    return {
        "tugas_akhir": {"id": ta.pk, "judul": ta.judul},
        "progres": tl.progres,
        "jumlah_diverifikasi": tl.jumlah_diverifikasi,
        "tahap_aktif": {"id": aktif.id, "nama": aktif.nama} if aktif else None,
        "milestone": tl.items,
    }


class MahasiswaMilestoneView(APIView):
    permission_classes = [IsMahasiswa]

    @extend_schema(summary="Timeline milestone milik mahasiswa", responses=TimelineSerializer)
    def get(self, request):
        semua = TugasAkhir.objects.filter(mahasiswa=request.user)
        ta = semua.filter(status=TugasAkhir.Status.AKTIF).first() or semua.order_by("-id").first()
        return Response(TimelineSerializer(_payload_timeline(ta)).data)


class _DosenMilestoneView(APIView):
    permission_classes = [IsDosen]

    def ambil_milestone(self, request, pk):
        """Hanya pembimbing utama TA tersebut; selain itu 404 (BR-09)."""
        qs = Milestone.objects.select_related("tugas_akhir__mahasiswa").filter(
            tugas_akhir__penugasan__dosen=request.user,
            tugas_akhir__penugasan__peran=Penugasan.Peran.UTAMA,
        )
        return get_object_or_404(qs, pk=pk)

    def hasil(self, milestone):
        tl = timeline_ta(milestone.tugas_akhir)
        item = next(i for i in tl.items if i.id == milestone.pk)
        return Response(AksiResponseSerializer({"milestone": item, "progres": tl.progres}).data)

    def konflik(self, exc):
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)


class TargetView(_DosenMilestoneView):
    @extend_schema(
        summary="Tetapkan, ubah, atau hapus target milestone",
        request=TargetSerializer,
        responses={200: AksiResponseSerializer, 409: DetailSerializer},
    )
    def patch(self, request, pk):
        milestone = self.ambil_milestone(request, pk)
        serializer = TargetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tetapkan_target(milestone, serializer.validated_data["target"], request.user)
        except MilestoneError as exc:
            return self.konflik(exc)
        return self.hasil(milestone)


class VerifikasiView(_DosenMilestoneView):
    @extend_schema(
        summary="Verifikasi milestone (tahap aktif)",
        request=VerifikasiSerializer,
        responses={200: AksiResponseSerializer, 409: DetailSerializer},
    )
    def post(self, request, pk):
        milestone = self.ambil_milestone(request, pk)
        serializer = VerifikasiSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            verifikasi(milestone, serializer.validated_data["tingkat_penyelesaian"], request.user)
        except MilestoneError as exc:
            return self.konflik(exc)
        return self.hasil(milestone)