from rest_framework import serializers

from .models import Bimbingan
from .services import JadwalError, validasi_rentang_waktu


class BimbinganRequestSerializer(serializers.Serializer):
    dosen_id = serializers.IntegerField(min_value=1)
    mulai = serializers.DateTimeField()
    selesai = serializers.DateTimeField()
    mode = serializers.ChoiceField(choices=Bimbingan.Mode.choices)
    lokasi_atau_tautan = serializers.CharField(required=False, allow_blank=True, max_length=500, default="")
    agenda = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")

    def validate(self, attrs):
        try:
            validasi_rentang_waktu(attrs["mulai"], attrs["selesai"])
        except JadwalError as exc:
            raise serializers.ValidationError({"mulai": str(exc)}) from None
        return attrs


class RescheduleSerializer(serializers.Serializer):
    mulai = serializers.DateTimeField()
    selesai = serializers.DateTimeField()
    mode = serializers.ChoiceField(choices=Bimbingan.Mode.choices)
    lokasi_atau_tautan = serializers.CharField(required=False, allow_blank=True, max_length=500, default="")
    agenda = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")

    def validate(self, attrs):
        try:
            validasi_rentang_waktu(attrs["mulai"], attrs["selesai"])
        except JadwalError as exc:
            raise serializers.ValidationError({"mulai": str(exc)}) from None
        return attrs


class SetujuiSerializer(serializers.Serializer):
    lokasi_atau_tautan = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)


class TolakSerializer(serializers.Serializer):
    alasan = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)


class UsulkanWaktuSerializer(serializers.Serializer):
    mulai = serializers.DateTimeField()
    selesai = serializers.DateTimeField()
    lokasi_atau_tautan = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        try:
            validasi_rentang_waktu(attrs["mulai"], attrs["selesai"])
        except JadwalError as exc:
            raise serializers.ValidationError({"mulai": str(exc)}) from None
        return attrs


class DosenTujuanSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    identifier = serializers.CharField()
    nama_lengkap = serializers.CharField()
    peran = serializers.CharField()
    peran_label = serializers.CharField()


class BimbinganItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    tugas_akhir = serializers.DictField()
    mahasiswa = serializers.DictField()
    dosen = serializers.DictField()
    mulai = serializers.DateTimeField()
    selesai = serializers.DateTimeField()
    mode = serializers.ChoiceField(choices=Bimbingan.Mode.choices)
    mode_label = serializers.CharField()
    lokasi_atau_tautan = serializers.CharField(allow_blank=True)
    agenda = serializers.CharField(allow_blank=True)
    status = serializers.ChoiceField(choices=Bimbingan.Status.choices)
    status_label = serializers.CharField()
    menggantikan = serializers.IntegerField(allow_null=True)
    alasan_penolakan = serializers.CharField(allow_blank=True)
    dibuat_pada = serializers.DateTimeField()


class JadwalMahasiswaResponseSerializer(serializers.Serializer):
    tugas_akhir = serializers.DictField(allow_null=True)
    dosen_tujuan = DosenTujuanSerializer(many=True)
    mendatang = BimbinganItemSerializer(many=True)
    riwayat = BimbinganItemSerializer(many=True)


class PermohonanDosenResponseSerializer(serializers.Serializer):
    jumlah = serializers.IntegerField()
    hasil = BimbinganItemSerializer(many=True)
