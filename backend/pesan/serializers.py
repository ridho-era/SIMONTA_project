from rest_framework import serializers

from .models import Percakapan, Pesan
from .services import url_lampiran
from .validators import LampiranPesanError, MAKS_UKURAN, validasi_lampiran


class KirimPesanSerializer(serializers.Serializer):
    isi = serializers.CharField(required=False, allow_blank=True, max_length=10000, default="")
    lampiran = serializers.FileField(required=False, allow_empty_file=False)
    dokumen_versi = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate_lampiran(self, value):
        try:
            validasi_lampiran(value)
        except LampiranPesanError as exc:
            raise serializers.ValidationError(str(exc)) from None
        return value

    def validate(self, attrs):
        if not attrs.get("isi", "").strip() and not attrs.get("lampiran") and not attrs.get("dokumen_versi"):
            raise serializers.ValidationError(
                "Isi pesan, lampiran, atau konteks dokumen harus diisi."
            )
        if attrs.get("lampiran") is not None and attrs["lampiran"].size > MAKS_UKURAN:
            raise serializers.ValidationError({"lampiran": "Ukuran lampiran maksimal 15 MB."})
        return attrs


class LawanBicaraSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    identifier = serializers.CharField()
    nama_lengkap = serializers.CharField()
    role = serializers.CharField()
    peran = serializers.CharField(allow_blank=True)
    peran_label = serializers.CharField(allow_blank=True)


class PesanTerakhirSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    isi = serializers.CharField(allow_blank=True)
    nama_lampiran = serializers.CharField(allow_blank=True)
    pengirim_id = serializers.IntegerField()
    dibuat_pada = serializers.DateTimeField()


class PercakapanListSerializer(serializers.ModelSerializer):
    tugas_akhir = serializers.SerializerMethodField()
    lawan_bicara = serializers.SerializerMethodField()
    pesan_terakhir = serializers.SerializerMethodField()
    jumlah_belum_dibaca = serializers.IntegerField(read_only=True)

    class Meta:
        model = Percakapan
        fields = [
            "id", "tugas_akhir", "lawan_bicara", "pesan_terakhir",
            "jumlah_belum_dibaca", "diubah_pada",
        ]

    def get_tugas_akhir(self, obj):
        return {"id": obj.tugas_akhir_id, "judul": obj.tugas_akhir.judul}

    def get_lawan_bicara(self, obj):
        user = self.context["request"].user
        lawan = obj.lawan_bicara(user)
        penugasan = obj.tugas_akhir.penugasan.filter(dosen=obj.dosen).first()
        peran = penugasan.peran if penugasan else ""
        peran_label = penugasan.get_peran_display() if penugasan else ""
        return {
            "id": lawan.pk,
            "identifier": lawan.identifier,
            "nama_lengkap": lawan.nama_lengkap,
            "role": lawan.role,
            "peran": peran if user.role == "mahasiswa" else "",
            "peran_label": peran_label if user.role == "mahasiswa" else "",
        }

    def get_pesan_terakhir(self, obj):
        pesan = getattr(obj, "pesan_terakhir", None)
        if pesan is None:
            return None
        return {
            "id": pesan.pk,
            "isi": pesan.isi,
            "nama_lampiran": pesan.nama_lampiran,
            "pengirim_id": pesan.pengirim_id,
            "dibuat_pada": pesan.dibuat_pada,
        }


class PesanItemSerializer(serializers.ModelSerializer):
    pengirim = serializers.SerializerMethodField()
    saya_pengirim = serializers.SerializerMethodField()
    lampiran_url = serializers.SerializerMethodField()
    dokumen_versi = serializers.SerializerMethodField()

    class Meta:
        model = Pesan
        fields = [
            "id", "pengirim", "saya_pengirim", "isi", "nama_lampiran",
            "lampiran_url", "dokumen_versi", "dibuat_pada", "dibaca_pada",
        ]

    def get_pengirim(self, obj):
        return {
            "id": obj.pengirim_id,
            "nama_lengkap": obj.pengirim.nama_lengkap,
            "identifier": obj.pengirim.identifier,
            "role": obj.pengirim.role,
        }

    def get_saya_pengirim(self, obj):
        return obj.pengirim_id == self.context["request"].user.pk

    def get_lampiran_url(self, obj):
        if not obj.lampiran:
            return ""
        return url_lampiran(self.context["request"].user, obj)

    def get_dokumen_versi(self, obj):
        versi = obj.dokumen_versi
        if not versi:
            return None
        milestone = versi.dokumen.milestone
        return {
            "id": versi.pk,
            "nama_asli": versi.nama_asli,
            "nomor_versi": versi.nomor_versi,
            "milestone": milestone.nama,
        }


class PesanDibacaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dibaca_pada = serializers.DateTimeField()


class ThreadSerializer(serializers.Serializer):
    percakapan = serializers.DictField()
    dokumen_tersedia = serializers.ListField(child=serializers.DictField())
    pesan = PesanItemSerializer(many=True)
    pesan_dibaca = PesanDibacaSerializer(many=True)
