from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDosen, IsMahasiswa

from .models import ChecklistRevisi, Review
from .serializers import (
    ChecklistInputSerializer,
    ChecklistSerializer,
    ChecklistUpdateSerializer,
    DetailSerializer,
    ReviewDrafInputSerializer,
    ReviewDrafSerializer,
)
from .services import (
    ReviewError,
    checklist_mahasiswa_terjangkau,
    daftar_review_mahasiswa,
    detail_dosen,
    detail_review_mahasiswa,
    daftar_review_dosen,
    review_mahasiswa_terjangkau,
    simpan_draf,
    terbitkan_review,
)


class DaftarReviewDosenView(APIView):
    permission_classes = [IsDosen]

    @extend_schema(summary="Antrean berkas yang perlu direview oleh pembimbing utama atau pendamping")
    def get(self, request):
        return Response(daftar_review_dosen(request.user))


class DetailReviewDosenView(APIView):
    permission_classes = [IsDosen]

    @extend_schema(summary="Detail berkas dan catatan review sebelumnya untuk pembimbing")
    def get(self, request, versi_id):
        return Response(detail_dosen(request.user, versi_id))


class DrafReviewDosenView(APIView):
    permission_classes = [IsDosen]

    @extend_schema(
        summary="Buat atau perbarui draf review (autosave)",
        request=ReviewDrafInputSerializer,
        responses={200: ReviewDrafSerializer, 404: DetailSerializer},
    )
    def put(self, request, versi_id):
        serializer = ReviewDrafInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draf = simpan_draf(user=request.user, versi_id=versi_id, data=serializer.validated_data)
        return Response(ReviewDrafSerializer(draf).data)


class TerbitkanReviewDosenView(APIView):
    permission_classes = [IsDosen]

    @extend_schema(
        summary="Terbitkan draf review secara atomik dan idempoten",
        request=None,
        responses={200: ReviewDrafSerializer, 400: DetailSerializer, 404: DetailSerializer},
    )
    def post(self, request, review_id):
        try:
            review, sudah_terbit = terbitkan_review(user=request.user, review_id=review_id)
        except ReviewError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"review": ReviewDrafSerializer(review).data, "sudah_terbit": sudah_terbit})


class DaftarReviewMahasiswaView(APIView):
    permission_classes = [IsMahasiswa]

    @extend_schema(summary="Daftar review terbit milik mahasiswa dan catatan awal yang dibagikan")
    def get(self, request):
        return Response(daftar_review_mahasiswa(request.user))


class DetailReviewMahasiswaView(APIView):
    permission_classes = [IsMahasiswa]

    @extend_schema(summary="Detail review yang telah diterbitkan untuk mahasiswa")
    def get(self, request, review_id):
        return Response(detail_review_mahasiswa(request.user, review_id))


class ChecklistReviewMahasiswaView(APIView):
    permission_classes = [IsMahasiswa]

    @extend_schema(
        summary="Baca checklist pribadi untuk review terbit",
        responses={200: ChecklistSerializer(many=True), 404: DetailSerializer},
    )
    def get(self, request, review_id):
        review_mahasiswa_terjangkau(request.user, review_id)
        items = ChecklistRevisi.objects.filter(review_id=review_id, mahasiswa=request.user)
        return Response(ChecklistSerializer(items, many=True).data)

    @extend_schema(
        summary="Tambah catatan checklist pribadi",
        request=ChecklistInputSerializer,
        responses={201: ChecklistSerializer, 404: DetailSerializer},
    )
    def post(self, request, review_id):
        review = review_mahasiswa_terjangkau(request.user, review_id)
        serializer = ChecklistInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = ChecklistRevisi.objects.create(
            review=review,
            mahasiswa=request.user,
            catatan=serializer.validated_data["catatan"],
        )
        return Response(ChecklistSerializer(item).data, status=status.HTTP_201_CREATED)


class ItemChecklistMahasiswaView(APIView):
    permission_classes = [IsMahasiswa]

    @extend_schema(
        summary="Ubah catatan atau status selesai checklist pribadi",
        request=ChecklistUpdateSerializer,
        responses={200: ChecklistSerializer, 404: DetailSerializer},
    )
    def patch(self, request, checklist_id):
        item = checklist_mahasiswa_terjangkau(request.user, checklist_id)
        serializer = ChecklistUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(item, field, value)
        item.save(update_fields=[*serializer.validated_data.keys(), "diubah_pada"])
        return Response(ChecklistSerializer(item).data)

    @extend_schema(summary="Hapus catatan checklist pribadi", request=None, responses={204: None})
    def delete(self, request, checklist_id):
        item = checklist_mahasiswa_terjangkau(request.user, checklist_id)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
