from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "dibuat_pada", "versi", "pemberi", "bagian_ringkas", "rekomendasi",
        "nilai", "status", "diterbitkan_pada",
    )
    list_filter = ("status", "rekomendasi")
    search_fields = (
        "versi__nama_asli", "pemberi__identifier",
        "versi__dokumen__milestone__tugas_akhir__mahasiswa__identifier",
    )
    list_select_related = ("pemberi", "versi__dokumen__milestone__tugas_akhir__mahasiswa")
    readonly_fields = (
        "versi", "pemberi", "bagian", "komentar", "nilai", "rekomendasi",
        "tenggat_revisi", "status", "diterbitkan_pada", "bagikan_catatan_awal",
        "dibuat_pada", "diubah_pada",
    )

    @admin.display(description="bagian")
    def bagian_ringkas(self, obj):
        return (obj.bagian or "—")[:60]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False