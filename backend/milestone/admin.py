from django.contrib import admin

from .models import Milestone


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    """Hanya lihat: target dan verifikasi adalah aksi pembimbing utama (BR-02, BR-03)."""

    list_display = (
        "tugas_akhir", "urutan", "nama", "bobot", "target",
        "tingkat_penyelesaian", "diverifikasi_oleh", "diverifikasi_pada",
    )
    list_filter = ("tugas_akhir__periode",)
    search_fields = ("tugas_akhir__mahasiswa__identifier", "tugas_akhir__mahasiswa__nama_lengkap", "nama")
    list_select_related = ("tugas_akhir__mahasiswa", "diverifikasi_oleh")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False