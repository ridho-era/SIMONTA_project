from django.contrib import admin

from .models import Percakapan, Pesan


class PesanInline(admin.TabularInline):
    model = Pesan
    extra = 0
    can_delete = False
    fields = ("dibuat_pada", "pengirim", "isi", "nama_lampiran", "dokumen_versi", "dibaca_pada")
    readonly_fields = fields
    ordering = ("-dibuat_pada",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Percakapan)
class PercakapanAdmin(admin.ModelAdmin):
    list_display = ("id", "mahasiswa", "dosen", "tugas_akhir", "diubah_pada")
    search_fields = (
        "tugas_akhir__mahasiswa__identifier",
        "tugas_akhir__mahasiswa__nama_lengkap",
        "dosen__identifier",
        "dosen__nama_lengkap",
        "tugas_akhir__judul",
    )
    list_select_related = ("tugas_akhir__mahasiswa", "dosen")
    readonly_fields = ("tugas_akhir", "dosen", "dibuat_pada", "diubah_pada")
    inlines = (PesanInline,)

    @admin.display(description="mahasiswa")
    def mahasiswa(self, obj):
        return obj.tugas_akhir.mahasiswa

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Pesan)
class PesanAdmin(admin.ModelAdmin):
    list_display = ("id", "percakapan", "pengirim", "dibuat_pada", "dibaca_pada", "nama_lampiran")
    list_filter = ("dibaca_pada",)
    search_fields = ("isi", "pengirim__identifier", "percakapan__tugas_akhir__mahasiswa__identifier")
    list_select_related = ("percakapan", "pengirim")
    readonly_fields = ("percakapan", "pengirim", "isi", "lampiran", "nama_lampiran", "dokumen_versi", "dibuat_pada", "dibaca_pada")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
