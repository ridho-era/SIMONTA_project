from rest_framework import serializers

from .services import Status


class TugasAkhirRingkasSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    judul = serializers.CharField()


class TahapAktifSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nama = serializers.CharField()


class MilestoneItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    urutan = serializers.IntegerField()
    nama = serializers.CharField()
    bobot = serializers.DecimalField(max_digits=5, decimal_places=2, coerce_to_string=False)
    target = serializers.DateField(allow_null=True)
    status = serializers.ChoiceField(choices=Status.CHOICES)
    tahap_aktif = serializers.BooleanField()
    terkunci = serializers.BooleanField()
    tingkat_penyelesaian = serializers.IntegerField()
    diverifikasi_pada = serializers.DateTimeField(allow_null=True)


class TimelineSerializer(serializers.Serializer):
    tugas_akhir = TugasAkhirRingkasSerializer(allow_null=True)
    progres = serializers.DecimalField(max_digits=5, decimal_places=2, coerce_to_string=False)
    jumlah_diverifikasi = serializers.IntegerField()
    tahap_aktif = TahapAktifSerializer(allow_null=True)
    milestone = MilestoneItemSerializer(many=True)


class AksiResponseSerializer(serializers.Serializer):
    milestone = MilestoneItemSerializer()
    progres = serializers.DecimalField(max_digits=5, decimal_places=2, coerce_to_string=False)


class TargetSerializer(serializers.Serializer):
    target = serializers.DateField(allow_null=True)


class VerifikasiSerializer(serializers.Serializer):
    tingkat_penyelesaian = serializers.IntegerField(min_value=0, max_value=100, required=False, default=100)


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()