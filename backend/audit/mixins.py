from .models import AuditLog
from .services import catat_audit, diff, snapshot


class AuditAdminMixin:
    """Mencatat tambah/ubah/hapus dari Django admin ke AuditLog (BR-10).

    Pasang SEBELUM ModelAdmin: class XAdmin(AuditAdminMixin, admin.ModelAdmin).
    Admin menjalankan changeform dalam satu transaksi, jadi bila penyimpanan gagal
    baris audit ikut dibatalkan.
    """

    # Field yang tidak perlu dicatat (mis. kolom penjaga internal).
    audit_exclude_fields = ()

    def _audit_snapshot(self, obj):
        return snapshot(obj, self.audit_exclude_fields)

    def _audit_state_db(self, obj):
        """Keadaan objek di database sebelum disimpan (None bila objek baru)."""
        if obj.pk is None:
            return None
        lama = type(obj)._default_manager.filter(pk=obj.pk).first()
        return self._audit_snapshot(lama) if lama is not None else None

    def _audit_catat_simpan(self, request, obj, sebelum):
        sesudah = self._audit_snapshot(obj)
        if sebelum is None:
            catat_audit(request.user, AuditLog.Aksi.TAMBAH, obj, sesudah=sesudah)
            return
        berubah_sebelum, berubah_sesudah = diff(sebelum, sesudah)
        if berubah_sebelum or berubah_sesudah:  # simpan tanpa perubahan tidak dicatat
            catat_audit(
                request.user,
                AuditLog.Aksi.UBAH,
                obj,
                sebelum=berubah_sebelum,
                sesudah=berubah_sesudah,
            )

    def save_model(self, request, obj, form, change):
        sebelum = self._audit_state_db(obj) if change else None
        super().save_model(request, obj, form, change)
        self._audit_catat_simpan(request, obj, sebelum)

    def delete_model(self, request, obj):
        pk, teks, sebelum = obj.pk, str(obj), self._audit_snapshot(obj)
        super().delete_model(request, obj)
        catat_audit(
            request.user,
            AuditLog.Aksi.HAPUS,
            obj,
            sebelum=sebelum,
            objek_id=pk,
            objek_repr=teks,
        )

    def delete_queryset(self, request, queryset):
        daftar = [(obj, obj.pk, str(obj), self._audit_snapshot(obj)) for obj in queryset]
        super().delete_queryset(request, queryset)
        for obj, pk, teks, sebelum in daftar:
            catat_audit(
                request.user,
                AuditLog.Aksi.HAPUS,
                obj,
                sebelum=sebelum,
                objek_id=pk,
                objek_repr=teks,
            )

    def save_formset(self, request, form, formset, change):
        """Mencatat baris inline (mis. Penugasan di TugasAkhir)."""
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:  # hapus dulu agar unique constraint tidak bentrok
            pk, teks, sebelum = obj.pk, str(obj), self._audit_snapshot(obj)
            obj.delete()
            catat_audit(
                request.user,
                AuditLog.Aksi.HAPUS,
                obj,
                sebelum=sebelum,
                objek_id=pk,
                objek_repr=teks,
            )
        for obj in instances:
            sebelum = self._audit_state_db(obj)
            obj.save()
            self._audit_catat_simpan(request, obj, sebelum)
        formset.save_m2m()