from rest_framework import serializers

from .models import ChecklistRevisi, Review


class ReviewDrafInputSerializer(serializers.Serializer):
    bagian = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    komentar = serializers.CharField(required=False, allow_blank=True, max_length=10000)
    nilai = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=100)
    rekomendasi = serializers.ChoiceField(
        choices=Review.Rekomendasi.choices, required=False, allow_null=True
    )
    tenggat_revisi = serializers.DateField(required=False, allow_null=True)
    bagikan_catatan_awal = serializers.BooleanField(required=False)


class ReviewDrafSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = [
            "id", "bagian", "komentar", "nilai", "rekomendasi",
            "tenggat_revisi", "status", "bagikan_catatan_awal", "diubah_pada",
        ]
        read_only_fields = ["id", "status", "diubah_pada"]


class ChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistRevisi
        fields = ["id", "catatan", "selesai", "dibuat_pada", "diubah_pada"]
        read_only_fields = ["id", "dibuat_pada", "diubah_pada"]


class ChecklistInputSerializer(serializers.Serializer):
    catatan = serializers.CharField(max_length=1000, allow_blank=False, trim_whitespace=True)


class ChecklistUpdateSerializer(serializers.Serializer):
    catatan = serializers.CharField(required=False, max_length=1000, allow_blank=False, trim_whitespace=True)
    selesai = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Isi setidaknya satu perubahan.")
        return attrs


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()