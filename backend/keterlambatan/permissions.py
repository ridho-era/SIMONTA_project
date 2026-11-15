from rest_framework.permissions import BasePermission

from accounts.models import Role


class IsDosenAtauAdmin(BasePermission):
    message = "Hanya pembimbing utama atau Admin Prodi yang dapat mengakses fitur ini."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not user.must_change_password
            and user.role in {Role.DOSEN, Role.ADMIN}
        )
