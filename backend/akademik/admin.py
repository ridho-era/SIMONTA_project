from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.utils.text import Truncator

from audit.mixins import AuditAdminMixin
from milestone.services import buat_milestone_untuk_ta

from .models import (
    BOBOT_TOTAL,
    JenisSanksi,
    KonfigurasiDenda,
    MilestoneTemplate,
    Penugasan,
    PeriodeAkademik,
    ProgramStudi,
    TugasAkhir,
)


class PenugasanInlineFormSet(BaseInlineFormSet):
    """Memeriksa kondisi akhir seluruh baris penugasan dalam satu form."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        dosen_terpakai = set()
        jumlah_utama = 0
        for form in self.forms:
            data = getattr(form, "cleaned_data", None)
            if not data or data.get("DELETE"):
                continue
            dosen = data.get("dosen")
            if dosen is None:
                continue
            if dosen.pk in dosen_terpakai:
                raise ValidationError(
                    "Dosen yang sama tidak boleh ditugaskan dua kali pada satu tugas akhir."
                )
            dosen_terpakai.add(dosen.pk)
            if data.get("peran") == Penugasan.Peran.UTAMA:
                jumlah_utama += 1
        if jumlah_utama > 1:
            raise ValidationError("Satu tugas akhir hanya boleh memiliki satu pembimbing utama.")


class PenugasanInline(admin.TabularInline):
    model = Penugasan
    formset = PenugasanInlineFormSet
    extra = 0
    autocomplete_fields = ["dosen"]


class TugasAkhirForm(forms.ModelForm):
    class Meta:
        model = TugasAkhir
        fields = "__all__"

    def clean(self):
        data = super().clean()
        if self.instance.pk is None:  # TA baru akan dibuatkan milestone dari template
            try:
                MilestoneTemplate.pastikan_total_valid()
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return data


@admin.register(ProgramStudi)
class ProgramStudiAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("nama",)
    search_fields = ("nama",)


@admin.register(PeriodeAkademik)
class PeriodeAkademikAdmin(AuditAdminMixin, admin.ModelAdmin):
    audit_exclude_fields = ("slot_aktif",)
    list_display = ("label", "tanggal_mulai", "tanggal_selesai", "aktif")
    list_filter = ("aktif",)
    search_fields = ("label",)


@admin.register(TugasAkhir)
class TugasAkhirAdmin(AuditAdminMixin, admin.ModelAdmin):
    audit_exclude_fields = ("slot_aktif",)
    form = TugasAkhirForm
    list_display = ("mahasiswa", "periode", "judul_ringkas", "jenis_penelitian", "status")
    list_filter = ("status", "periode", "jenis_penelitian")
    search_fields = ("mahasiswa__identifier", "mahasiswa__nama_lengkap", "judul")
    autocomplete_fields = ["mahasiswa", "periode"]
    list_select_related = ("mahasiswa", "periode")
    inlines = [PenugasanInline]

    @admin.display(description="Judul")
    def judul_ringkas(self, obj):
        return Truncator(obj.judul).chars(60)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            buat_milestone_untuk_ta(obj)  # eksplisit, bukan signal (BR-01)


@admin.register(MilestoneTemplate)
class MilestoneTemplateAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("urutan", "nama", "bobot", "aktif")
    list_filter = ("aktif",)
    search_fields = ("nama",)
    ordering = ("urutan",)

    def changelist_view(self, request, extra_context=None):
        if not MilestoneTemplate.objects.filter(aktif=True).exists():
            messages.warning(request, "Belum ada template milestone aktif.")
        else:
            total = MilestoneTemplate.total_bobot_aktif()
            if total == BOBOT_TOTAL:
                messages.success(request, "Total bobot template aktif: 100. Template valid.")
            else:
                messages.warning(
                    request,
                    f"Total bobot template aktif saat ini {total} dari 100. "
                    "Template harus tepat 100 sebelum tugas akhir dapat dibuatkan milestone.",
                )
        return super().changelist_view(request, extra_context)


@admin.register(KonfigurasiDenda)
class KonfigurasiDendaAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "periode",
        "jenis",
        "tarif",
        "toleransi_hari",
        "batas_per_catatan",
        "label_simulasi",
    )
    list_filter = ("periode", "jenis", "label_simulasi")
    search_fields = ("periode__label",)
    autocomplete_fields = ["periode"]
    list_select_related = ("periode",)


@admin.register(JenisSanksi)
class JenisSanksiAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("nama", "aktif")
    list_filter = ("aktif",)
    search_fields = ("nama",)