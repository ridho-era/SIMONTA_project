from rest_framework import serializers


class PengajuanKeberatanSerializer(serializers.Serializer):
    alasan = serializers.CharField(max_length=10000, trim_whitespace=True)
    aksi = serializers.ChoiceField(choices=["simpan_draf", "ajukan"])
    bukti = serializers.FileField(required=False, allow_null=True, use_url=False)


class CatatanAdministrasiSerializer(serializers.Serializer):
    tugas_akhir_id = serializers.IntegerField(min_value=1)
    nama_dokumen = serializers.CharField(max_length=255, trim_whitespace=True)
    tenggat = serializers.DateField(input_formats=["%Y-%m-%d"])
    realisasi = serializers.DateField(required=False, allow_null=True, input_formats=["%Y-%m-%d"])


class KeputusanCatatanSerializer(serializers.Serializer):
    aksi = serializers.ChoiceField(choices=["konfirmasi", "batalkan"])
    catatan_peninjau = serializers.CharField(required=False, allow_blank=True, max_length=10000)
    jenis_sanksi_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class KeputusanKeberatanSerializer(serializers.Serializer):
    aksi = serializers.ChoiceField(choices=["terima", "minta_kelengkapan"])
    catatan_peninjau = serializers.CharField(required=False, allow_blank=True, max_length=10000)
