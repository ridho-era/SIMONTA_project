from rest_framework import serializers

from .models import HalamanBantuan


class HalamanBantuanSerializer(serializers.ModelSerializer):
    class Meta:
        model = HalamanBantuan
        fields = ["id", "judul", "slug", "ringkasan", "konten", "diperbarui_pada"]
        read_only_fields = fields
