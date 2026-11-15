from django.contrib import admin

from .models import Notifikasi, PengaturanNotifikasi, PengingatTerjadwal


@admin.register(Notifikasi)
class NotifikasiAdmin(admin.ModelAdmin):
    """Notifikasi dibuat sistem; admin hanya dapat meninjau riwayat."""

    list_display = ("dibuat_pada", "user", "jenis", "judul", "dibaca_pada", "email_dikirim_pada")
    list_filter = ("jenis", "dibaca_pada")
    search_fields = ("user__identifier", "user__nama_lengkap", "judul")
    list_select_related = ("user",)
    readonly_fields = [field.name for field in Notifikasi._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PengaturanNotifikasi)
class PengaturanNotifikasiAdmin(admin.ModelAdmin):
    list_display = ("user", "pengingat_aktif", "kanal_email", "ringkasan_mingguan", "jam_kirim", "zona_waktu")
    list_filter = ("pengingat_aktif", "kanal_email", "ringkasan_mingguan")
    search_fields = ("user__identifier", "user__nama_lengkap")
    readonly_fields = [field.name for field in PengaturanNotifikasi._meta.fields]


@admin.register(PengingatTerjadwal)
class PengingatTerjadwalAdmin(admin.ModelAdmin):
    list_display = ("pengguna", "milestone", "offset_hari", "tanggal_target", "jadwal_kirim", "status", "dikirim_pada")
    list_filter = ("status", "offset_hari")
    search_fields = ("pengguna__identifier", "milestone__nama")
    list_select_related = ("pengguna", "milestone")
    readonly_fields = [field.name for field in PengingatTerjadwal._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
