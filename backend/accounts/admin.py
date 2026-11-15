from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, ReadOnlyPasswordHashField
from django.db import transaction

from audit.mixins import AuditAdminMixin
from audit.models import AuditLog
from audit.services import catat_audit

from .models import User
from .passwords import buat_password_sementara


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("identifier", "role", "nama_lengkap", "gelar", "program_studi", "email_akademik", "telepon")


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Password disimpan sebagai hash dan tidak dapat dilihat. Untuk membuat "
            "password sementara, gunakan aksi 'Reset password' pada daftar pengguna."
        ),
    )

    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(AuditAdminMixin, BaseUserAdmin):
    # Perubahan NPM/NIP, role, email akademik, dan status akun tercatat di AuditLog (BR-10).
    # Password tidak pernah dicatat; last_login berubah tiap login sehingga dikecualikan.
    audit_exclude_fields = ("last_login",)

    form = UserChangeForm
    add_form = UserCreationForm

    list_display = (
        "identifier",
        "nama_lengkap",
        "role",
        "email_akademik",
        "program_studi",
        "is_active",
        "must_change_password",
    )
    list_filter = ("role", "is_active", "must_change_password")
    search_fields = ("identifier", "nama_lengkap", "email_akademik")
    autocomplete_fields = ("program_studi",)
    ordering = ("identifier",)
    readonly_fields = ("last_login", "date_joined")
    actions = ["reset_password_sementara"]

    fieldsets = (
        (None, {"fields": ("identifier", "password")}),
        (
            "Data akun",
            {"fields": ("role", "nama_lengkap", "gelar", "program_studi", "email_akademik", "telepon", "foto")},
        ),
        ("Status", {"fields": ("is_active", "must_change_password")}),
        (
            "Hak akses Django admin",
            {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Riwayat", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "identifier",
                    "role",
                    "nama_lengkap",
                    "gelar",
                    "program_studi",
                    "email_akademik",
                    "telepon",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        # Akun baru dari admin memakai password yang diberikan admin: wajib diganti.
        if not change:
            obj.must_change_password = True
        super().save_model(request, obj, form, change)

    @admin.action(description="Reset password (buat password sementara)")
    def reset_password_sementara(self, request, queryset):
        for user in queryset:
            temp_password = buat_password_sementara()
            with transaction.atomic():
                user.set_password(temp_password)
                user.must_change_password = True
                user.save(update_fields=["password", "must_change_password"])
                catat_audit(
                    request.user,
                    AuditLog.Aksi.RESET_PASSWORD,
                    user,
                    keterangan="Password sementara dibuat; wajib ganti saat masuk pertama.",
                )
            self.message_user(
                request,
                f"{user.identifier}: password sementara = {temp_password} "
                "(hanya tampil sekali; serahkan ke pengguna lewat jalur aman).",
                level=messages.WARNING,
            )