from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.sessions.models import Session
from django.core.files.storage import default_storage
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditLog
from audit.services import catat_audit, diff, snapshot

from .authentication import CsrfEnforcedAuthentication
from .lockout import is_locked_out, lockout_response
from .permissions import IsDosen, IsMahasiswa
from .serializers import (
    ChangePasswordSerializer,
    CsrfTokenSerializer,
    DetailSerializer,
    LoginSerializer,
    ProfilSerializer,
    UserSerializer,
)

# Pesan sama untuk semua penyebab gagal masuk agar tidak membocorkan informasi akun.
GENERIC_LOGIN_ERROR = "NPM/NIP atau password tidak valid."


class CsrfView(APIView):
    """Menetapkan cookie CSRF dan mengembalikan tokennya."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Ambil token CSRF",
        auth=[],
        responses={200: CsrfTokenSerializer},
    )
    def get(self, request):
        return Response({"csrfToken": get_token(request._request)})


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [CsrfEnforcedAuthentication]

    @extend_schema(
        summary="Masuk ke SIMONTA",
        auth=[],
        request=LoginSerializer,
        responses={200: UserSerializer, 401: DetailSerializer, 429: DetailSerializer},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # django-axes membutuhkan HttpRequest asli dan kunci kredensial "username".
        django_request = request._request

        # Tolak lebih awal bila akun+IP sudah terkunci, sebelum password diperiksa.
        if is_locked_out(django_request, data["identifier"]):
            return lockout_response(django_request)

        try:
            user = authenticate(
                request=django_request,
                username=data["identifier"],
                password=data["password"],
            )
        except PermissionDenied:
            return lockout_response(django_request)

        if getattr(django_request, "axes_locked_out", False):
            return lockout_response(django_request)

        # Akun hanya boleh masuk lewat tipe yang sesuai rolenya (admin tidak lewat sini).
        if user is None or user.role != data["tipe"]:
            return Response(
                {"detail": GENERIC_LOGIN_ERROR}, status=status.HTTP_401_UNAUTHORIZED
            )

        login(django_request, user)
        # Tanpa "ingat saya": sesi berakhir saat browser ditutup.
        # Dengan "ingat saya": 14 hari (SESSION_COOKIE_AGE).
        django_request.session.set_expiry(
            settings.SESSION_COOKIE_AGE if data["ingat_saya"] else 0
        )
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Keluar akun", request=None, responses={204: None})
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Data pengguna yang sedang masuk", responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Ganti password",
        request=ChangePasswordSerializer,
        responses={200: DetailSerializer},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        with transaction.atomic():
            user.set_password(serializer.validated_data["password_baru"])
            user.must_change_password = False
            user.save(update_fields=["password", "must_change_password"])
            catat_audit(
                user,
                AuditLog.Aksi.RESET_PASSWORD,
                user,
                keterangan="Pengguna mengganti password melalui keamanan akun.",
            )
        # Sesi ini tetap berlaku; hash sesi diperbarui setelah password berubah.
        update_session_auth_hash(request._request, user)
        return Response({"detail": "Password berhasil diubah."})


class ProfilView(APIView):
    permission_classes = [IsMahasiswa | IsDosen]

    @extend_schema(summary="Profil pengguna portal", responses=ProfilSerializer)
    def get(self, request):
        user = get_user_model().objects.select_related("program_studi").get(
    pk=request.user.pk
)
        return Response(ProfilSerializer(user).data)

    @extend_schema(
        summary="Ubah informasi pribadi profil",
        request=ProfilSerializer,
        responses=ProfilSerializer,
    )
    def patch(self, request):
        user = get_user_model().objects.select_related("program_studi").get(
    pk=request.user.pk
)
        sebelum = snapshot(user)
        foto_lama = user.foto.name if user.foto else None
        serializer = ProfilSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
            sesudah = snapshot(user)
            sebelum_ubah, sesudah_ubah = diff(sebelum, sesudah)
            if sebelum_ubah:
                catat_audit(
                    request.user,
                    AuditLog.Aksi.UBAH,
                    user,
                    sebelum=sebelum_ubah,
                    sesudah=sesudah_ubah,
                    keterangan="Pengguna memperbarui informasi profil.",
                )
            foto_baru = user.foto.name if user.foto else None
            if foto_lama and foto_lama != foto_baru:
                transaction.on_commit(lambda nama=foto_lama: default_storage.delete(nama))
        return Response(ProfilSerializer(user).data)


class FotoProfilView(APIView):
    permission_classes = [IsMahasiswa | IsDosen]

    @extend_schema(summary="Ambil foto profil milik akun sendiri", responses={200: OpenApiTypes.BINARY})
    def get(self, request):
        foto = request.user.foto
        if not foto:
            return Response({"detail": "Foto profil belum tersedia."}, status=status.HTTP_404_NOT_FOUND)
        try:
            berkas = foto.open("rb")
        except (FileNotFoundError, OSError):
            return Response({"detail": "Berkas foto profil tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        content_type = "image/jpeg" if foto.name.lower().endswith((".jpg", ".jpeg")) else "image/png"
        response = FileResponse(berkas, content_type=content_type)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class LogoutOtherSessionsView(APIView):
    permission_classes = [IsDosen]

    @extend_schema(summary="Keluar dari perangkat lain", request=None)
    def post(self, request):
        user = request.user
        sesi_saat_ini = request.session.session_key
        milik_user = []
        queryset = Session.objects.filter(expire_date__gt=timezone.now()).exclude(
            session_key=sesi_saat_ini
        )
        for sesi in queryset.iterator():
            if sesi.get_decoded().get("_auth_user_id") == str(user.pk):
                milik_user.append(sesi.session_key)
        with transaction.atomic():
            if milik_user:
                Session.objects.filter(session_key__in=milik_user).delete()
            catat_audit(
                user,
                AuditLog.Aksi.UBAH,
                user,
                sebelum={"jumlah_sesi_perangkat_lain": len(milik_user)},
                sesudah={"jumlah_sesi_perangkat_lain": 0},
                keterangan="Pengguna mengeluarkan sesi dari perangkat lain.",
            )
        return Response({
            "detail": "Sesi di perangkat lain berhasil dikeluarkan.",
            "jumlah_sesi_dikeluarkan": len(milik_user),
            "sesi_saat_ini_dipertahankan": True,
        })
