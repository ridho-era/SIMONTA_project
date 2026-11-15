from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Hanya baca: audit log tidak boleh ditambah, diubah, atau dihapus lewat admin."""

    list_display = (
        "waktu",
        "aktor_identifier",
        "aksi",
        "objek_tipe",
        "objek_id",
        "objek_repr",
        "keterangan",
    )
    list_filter = ("aksi", "objek_tipe")
    search_fields = ("aktor_identifier", "objek_repr", "objek_id", "keterangan")
    date_hierarchy = "waktu"
    readonly_fields = (
        "aktor",
        "aktor_identifier",
        "aksi",
        "objek_tipe",
        "objek_id",
        "objek_repr",
        "keterangan",
        "sebelum",
        "sesudah",
        "waktu",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False