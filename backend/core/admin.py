from django.contrib import admin

from audit.mixins import AuditAdminMixin

from .models import HalamanBantuan


@admin.register(HalamanBantuan)
class HalamanBantuanAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("judul", "slug", "aktif", "urutan", "diperbarui_pada")
    list_filter = ("aktif",)
    search_fields = ("judul", "slug", "ringkasan", "konten")
    list_editable = ("aktif", "urutan")
    prepopulated_fields = {"slug": ("judul",)}
    readonly_fields = ("diperbarui_pada",)
