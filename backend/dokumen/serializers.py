from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from milestone.serializers import TugasAkhirRingkasSerializer

from .models import DokumenVersi
from .services import url_pratinjau, url_unduh
from .validators import MAKS_UKURAN


class MilestoneRingkasSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    urutan = serializers.IntegerField()
    nama = serializers.CharField()


class UnggahSerializer(serializers.Serializer):
    milestone = serializers.IntegerField()
    berkas = serializers.FileField(allow_empty_file=False, max_length=255)
    catatan = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")


class VersiSerializer(serializers.ModelSerializer):
    milestone = serializers.SerializerMethodField()
    unduh_url = serializers.SerializerMethodField()
    pratinjau_url = serializers.SerializerMethodField()
    review_id = serializers.SerializerMethodField()
    nilai_review = serializers.SerializerMethodField()
    ringkasan_feedback = serializers.SerializerMethodField()
    review_url = serializers.SerializerMethodField()

    class Meta:
        model = DokumenVersi
        fields = [
            "id", "milestone", "nomor_versi", "nama_asli", "halaman", "ukuran",
            "status", "catatan", "diunggah_pada", "unduh_url", "pratinjau_url",
            "review_id", "nilai_review", "ringkasan_feedback", "review_url",
        ]
        read_only_fields = fields

    @extend_schema_field(MilestoneRingkasSerializer)
    def get_milestone(self, obj):
        ms = obj.dokumen.milestone
        return {"id": ms.pk, "urutan": ms.urutan, "nama": ms.nama}

    def get_unduh_url(self, obj) -> str:
        return url_unduh(self.context["request"].user, obj)

    def get_pratinjau_url(self, obj) -> str:
        return url_pratinjau(self.context["request"].user, obj)

    def _review_terbit(self, obj):
        tersedia = getattr(obj, "reviews_terbit", None)
        if tersedia is not None:
            return tersedia[0] if tersedia else None
        from review.models import Review
        return obj.reviews.filter(status=Review.Status.TERBIT).select_related("pemberi").first()

    def get_review_id(self, obj):
        review = self._review_terbit(obj)
        return review.pk if review else None

    def get_nilai_review(self, obj):
        review = self._review_terbit(obj)
        return review.nilai if review else None

    def get_ringkasan_feedback(self, obj):
        review = self._review_terbit(obj)
        return review.komentar[:180] if review else ""

    def get_review_url(self, obj):
        review = self._review_terbit(obj)
        return f"/mahasiswa/review/{review.pk}" if review else ""


class MilestoneOpsiSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    urutan = serializers.IntegerField()
    nama = serializers.CharField()
    dapat_unggah = serializers.BooleanField()
    alasan = serializers.CharField(allow_blank=True)


class RiwayatSerializer(serializers.Serializer):
    jumlah = serializers.IntegerField()
    halaman = serializers.IntegerField()
    total_halaman = serializers.IntegerField()
    hasil = VersiSerializer(many=True)


class BatasSerializer(serializers.Serializer):
    ukuran_maks_mb = serializers.IntegerField(default=MAKS_UKURAN // (1024 * 1024))
    ekstensi = serializers.ListField(child=serializers.CharField())


class DokumenSayaSerializer(serializers.Serializer):
    tugas_akhir = TugasAkhirRingkasSerializer(allow_null=True)
    milestone = MilestoneOpsiSerializer(many=True)
    riwayat = RiwayatSerializer()
    batas = BatasSerializer()