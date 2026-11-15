from rest_framework import serializers

from .models import PeriodeAkademik


class PeriodeAktifSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodeAkademik
        fields = ["id", "label", "tanggal_mulai", "tanggal_selesai"]
        read_only_fields = fields


class PeriodeAktifResponseSerializer(serializers.Serializer):
    periode = PeriodeAktifSerializer(allow_null=True)