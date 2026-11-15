import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from .models import Role

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=30)
    password = serializers.CharField(trim_whitespace=False, write_only=True)
    tipe = serializers.ChoiceField(choices=[Role.MAHASISWA, Role.DOSEN])
    ingat_saya = serializers.BooleanField(required=False, default=False)


class UserSerializer(serializers.ModelSerializer):
    punya_foto = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "identifier",
            "role",
            "nama_lengkap",
            "email_akademik",
            "telepon",
            "punya_foto",
            "must_change_password",
        ]
        read_only_fields = fields

    def get_punya_foto(self, obj) -> bool:
        return bool(obj.foto)


class ChangePasswordSerializer(serializers.Serializer):
    password_lama = serializers.CharField(trim_whitespace=False, write_only=True)
    password_baru = serializers.CharField(trim_whitespace=False, write_only=True)
    konfirmasi_password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate_password_lama(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password lama salah.")
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if attrs["password_baru"] != attrs["konfirmasi_password"]:
            raise serializers.ValidationError(
                {"konfirmasi_password": "Konfirmasi password tidak sama."}
            )
        if attrs["password_baru"] == attrs["password_lama"]:
            raise serializers.ValidationError(
                {"password_baru": "Password baru harus berbeda dari password lama."}
            )
        try:
            validate_password(attrs["password_baru"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password_baru": list(exc.messages)})
        return attrs


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()


class CsrfTokenSerializer(serializers.Serializer):
    csrfToken = serializers.CharField()

MAX_FOTO_PROFIL_BYTES = 2 * 1024 * 1024


class ProfilSerializer(serializers.ModelSerializer):
    punya_foto = serializers.SerializerMethodField()
    program_studi = serializers.SerializerMethodField()
    konteks_akademik = serializers.SerializerMethodField()
    foto_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "identifier", "role", "nama_lengkap", "gelar",
            "email_akademik", "telepon", "program_studi", "punya_foto",
            "foto_url", "konteks_akademik", "foto",
        ]
        read_only_fields = [
            "id", "identifier", "role", "email_akademik", "program_studi",
            "punya_foto", "foto_url", "konteks_akademik",
        ]
        extra_kwargs = {"foto": {"write_only": True, "required": False}}

    def to_internal_value(self, data):
        terlindungi = {
            "id", "identifier", "role", "email_akademik",
            "program_studi", "program_studi_id", "konteks_akademik",
            "judul", "periode", "pembimbing", "penguji", "foto_url", "punya_foto",
        }
        disertakan = terlindungi.intersection(set(data.keys()))
        if disertakan:
            raise serializers.ValidationError(
                {field: "Field ini hanya dapat diubah oleh admin Prodi." for field in disertakan}
            )
        if self.instance.role != Role.DOSEN and "gelar" in data:
            raise serializers.ValidationError({"gelar": "Gelar hanya dapat diubah pada profil dosen."})
        return super().to_internal_value(data)

    def validate_foto(self, berkas):
        if berkas.size > MAX_FOTO_PROFIL_BYTES:
            raise serializers.ValidationError("Ukuran foto maksimal 2 MB.")
        ekstensi = os.path.splitext(berkas.name)[1].lower()
        if ekstensi not in {".jpg", ".jpeg", ".png"}:
            raise serializers.ValidationError("Foto harus berformat JPG atau PNG.")
        try:
            berkas.seek(0)
            with Image.open(berkas) as gambar:
                if gambar.format not in {"JPEG", "PNG"}:
                    raise serializers.ValidationError("Isi foto harus berupa gambar JPG atau PNG yang valid.")
                if (gambar.format == "JPEG" and ekstensi not in {".jpg", ".jpeg"}) or (gambar.format == "PNG" and ekstensi != ".png"):
                    raise serializers.ValidationError("Ekstensi foto tidak sesuai dengan isi berkas.")
                gambar.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise serializers.ValidationError("Berkas bukan gambar JPG atau PNG yang valid.")
        finally:
            berkas.seek(0)
        return berkas

    def get_program_studi(self, obj):
        if not obj.program_studi_id:
            return None
        return {"id": obj.program_studi_id, "nama": obj.program_studi.nama}

    def get_foto_url(self, obj):
        if not obj.foto:
            return None
        return "/api/v1/profil/foto/"

    def get_konteks_akademik(self, obj):
        from akademik.models import Penugasan, TugasAkhir

        if obj.role == Role.MAHASISWA:
            ta = (
                TugasAkhir.objects.filter(mahasiswa=obj, status=TugasAkhir.Status.AKTIF)
                .select_related("periode")
                .first()
            )
            if ta is None:
                return {"tugas_akhir": None, "pembimbing": [], "penguji": []}
            penugasan = list(
                Penugasan.objects.filter(tugas_akhir=ta)
                .select_related("dosen")
                .order_by("peran", "dosen__nama_lengkap")
            )
            dosen = lambda item: {
                "identifier": item.dosen.identifier,
                "nama_lengkap": item.dosen.nama_lengkap,
                "gelar": item.dosen.gelar,
                "peran": item.get_peran_display(),
            }
            return {
                "tugas_akhir": {"id": ta.id, "judul": ta.judul, "status": ta.get_status_display()},
                "periode": {
                    "id": ta.periode_id, "label": ta.periode.label,
                    "tanggal_mulai": ta.periode.tanggal_mulai,
                    "tanggal_selesai": ta.periode.tanggal_selesai,
                },
                "pembimbing": [dosen(item) for item in penugasan if item.peran in {Penugasan.Peran.UTAMA, Penugasan.Peran.PENDAMPING}],
                "penguji": [dosen(item) for item in penugasan if item.peran == Penugasan.Peran.PENGUJI],
            }

        jumlah = (
            Penugasan.objects.filter(
                dosen=obj,
                peran__in=[Penugasan.Peran.UTAMA, Penugasan.Peran.PENDAMPING],
                tugas_akhir__status=TugasAkhir.Status.AKTIF,
            )
            .values("tugas_akhir__mahasiswa_id")
            .distinct()
            .count()
        )
        return {"jumlah_mahasiswa_bimbingan": jumlah}

    def get_punya_foto(self, obj):
        return bool(obj.foto)
