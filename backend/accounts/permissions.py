from rest_framework.permissions import BasePermission

from .models import Role

PASSWORD_CHANGE_REQUIRED = "Anda harus mengganti password sementara terlebih dahulu."


class _RolePermission(BasePermission):
    """Mengizinkan hanya pengguna aktif dengan role tertentu.

    Akun yang masih wajib ganti password ditolak di sini, sehingga aturan
    'wajib ganti saat masuk pertama' berlaku di sisi server, bukan hanya di UI.
    Endpoint me/, logout/, dan change-password/ memakai IsAuthenticated biasa.
    """

    role = None

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        if user.role != self.role:
            return False
        if user.must_change_password:
            self.message = PASSWORD_CHANGE_REQUIRED
            return False
        return True


class IsMahasiswa(_RolePermission):
    role = Role.MAHASISWA


class IsDosen(_RolePermission):
    role = Role.DOSEN


class IsAdminProdi(_RolePermission):
    role = Role.ADMIN