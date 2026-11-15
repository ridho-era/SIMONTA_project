from django.contrib import admin

from .models import DokumenVersi


@admin.register(DokumenVersi)
class DokumenVersiAdmin(admin.ModelAdmin):
    """Hanya lihat metadata. Berkas tidak punya tautan publik dan versi tidak dapat diubah (BR-04)."""

    list_display = ("diunggah_pada", "mahasiswa", "milestone", "nomor_versi", "nama_asli", "halaman", "ukuran", "status")
    list_filter = ("status",)
    search_fields = ("nama_asli", "dokumen__milestone__tugas_akhir__mahasiswa__identifier")
    list_select_related = ("dokumen__milestone__tugas_akhir__mahasiswa",)
    fields = (
        "dokumen", "nomor_versi", "nama_asli", "lokasi_penyimpanan", "halaman", "ukuran",
        "status", "catatan", "diunggah_pada",
    )
    readonly_fields = fields

    @admin.display(description="mahasiswa")
    def mahasiswa(self, obj):
        return obj.dokumen.milestone.tugas_akhir.mahasiswa

    @admin.display(description="milestone")
    def milestone(self, obj):
        return obj.dokumen.milestone

    @admin.display(description="lokasi penyimpanan")
    def lokasi_penyimpanan(self, obj):
        return obj.berkas.name

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False