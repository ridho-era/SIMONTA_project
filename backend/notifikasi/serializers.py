from rest_framework import serializers

from .models import Notifikasi, PengaturanNotifikasi


class NotifikasiSerializer(serializers.ModelSerializer):
    jenis_label = serializers.CharField(source="get_jenis_display", read_only=True)

    class Meta:
        model = Notifikasi
        fields = [
            "id", "jenis", "jenis_label", "judul", "isi", "tautan",
            "dibaca_pada", "dibuat_pada",
        ]


class PengaturanNotifikasiSerializer(serializers.ModelSerializer):
    zona_waktu_label = serializers.SerializerMethodField()

    class Meta:
        model = PengaturanNotifikasi
        fields = [
            "pengingat_aktif", "h_minus_7", "h_minus_3", "h_minus_1",
            "kanal_aplikasi", "kanal_email", "ringkasan_mingguan",
            "dokumen_feedback_aktif", "jadwal_bimbingan_aktif",
            "jam_kirim", "zona_waktu", "zona_waktu_label",
        ]
        read_only_fields = ["zona_waktu_label"]

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None and self.instance.user.role != "dosen":
            fields["dokumen_feedback_aktif"].read_only = True
            fields["jadwal_bimbingan_aktif"].read_only = True
        return fields

    def get_zona_waktu_label(self, obj):
        return "WIB (Asia/Jakarta)" if obj.zona_waktu == "Asia/Jakarta" else obj.zona_waktu

    def validate_zona_waktu(self, value):
        if value != "Asia/Jakarta":
            raise serializers.ValidationError("Saat ini SIMONTA menggunakan zona waktu WIB (Asia/Jakarta).")
        return value


class PratinjauPengingatItemSerializer(serializers.Serializer):
    milestone_id = serializers.IntegerField()
    milestone = serializers.CharField()
    mahasiswa = serializers.CharField()
    identifier = serializers.CharField()
    target = serializers.DateField()
    offset_hari = serializers.IntegerField()
    jadwal_kirim = serializers.DateTimeField()
    zona_waktu = serializers.CharField()
