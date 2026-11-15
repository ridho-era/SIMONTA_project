from django.contrib import admin

from audit.mixins import AuditAdminMixin

from .models import CatatanKeterlambatan, Keberatan, SanksiTercatat


@admin.register(CatatanKeterlambatan)
class CatatanKeterlambatanAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "tugas_akhir",
        "jenis",
        "tenggat",
        "realisasi",
        "nominal",
        "status_penilaian",
    )
    list_filter = ("jenis", "status_penilaian", "label_simulasi")
    search_fields = (
        "tugas_akhir__mahasiswa__identifier",
        "tugas_akhir__mahasiswa__nama_lengkap",
        "nama_dokumen",
    )
    readonly_fields = (
        "hari_terlambat",
        "hari_dikenai",
        "nominal",
        "dibuat_pada",
        "diubah_pada",
    )
    autocomplete_fields = ("tugas_akhir", "konfigurasi", "review", "milestone")
    list_select_related = ("tugas_akhir", "tugas_akhir__mahasiswa", "konfigurasi")


@admin.register(Keberatan)
class KeberatanAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("id", "catatan", "status", "diajukan_pada", "ditinjau_oleh")
    list_filter = ("status",)
    search_fields = (
        "catatan__tugas_akhir__mahasiswa__identifier",
        "catatan__tugas_akhir__mahasiswa__nama_lengkap",
        "alasan",
    )
    readonly_fields = ("nama_bukti", "ukuran_bukti", "diajukan_pada", "dibuat_pada", "diubah_pada")
    autocomplete_fields = ("catatan", "ditinjau_oleh")


@admin.register(SanksiTercatat)
class SanksiTercatatAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("catatan", "jenis_sanksi", "dicatat_oleh", "dibuat_pada")
    search_fields = (
        "catatan__tugas_akhir__mahasiswa__identifier",
        "catatan__tugas_akhir__mahasiswa__nama_lengkap",
        "jenis_sanksi__nama",
    )
    readonly_fields = ("dibuat_pada",)
    autocomplete_fields = ("catatan", "jenis_sanksi", "dicatat_oleh")
