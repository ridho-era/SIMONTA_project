from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manager untuk User kustom dengan identifier (NPM/NIP) sebagai username."""

    use_in_migrations = True

    def _create_user(self, identifier, password, **extra_fields):
        from .models import Role  # impor lokal untuk menghindari impor melingkar

        identifier = (identifier or "").strip()
        if not identifier:
            raise ValueError("Identifier (NPM/NIP) wajib diisi.")
        if extra_fields.get("role") not in Role.values:
            raise ValueError("Role wajib diisi: mahasiswa, dosen, atau admin.")
        if not extra_fields.get("nama_lengkap"):
            raise ValueError("Nama lengkap wajib diisi.")

        email = extra_fields.get("email_akademik")
        extra_fields["email_akademik"] = self.normalize_email(email) if email else None

        user = self.model(identifier=identifier, **extra_fields)
        user.set_password(password)  # password None -> tidak dapat dipakai masuk
        user.save(using=self._db)
        return user

    def create_user(self, identifier, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(identifier, password, **extra_fields)

    def create_superuser(self, identifier, password=None, **extra_fields):
        from .models import Role

        extra_fields.setdefault("role", Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields["role"] != Role.ADMIN:
            raise ValueError("Superuser harus memiliki role admin.")
        if extra_fields["is_staff"] is not True:
            raise ValueError("Superuser harus memiliki is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Superuser harus memiliki is_superuser=True.")

        return self._create_user(identifier, password, **extra_fields)