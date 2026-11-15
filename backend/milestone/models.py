from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

from akademik.models import MilestoneTemplate, TugasAkhir


class Milestone(models.Model):
    """Tahapan sebuah tugas akhir. Status (BR-02) dihitung di services.py, tidak disimpan."""

    tugas_akhir = models.ForeignKey(TugasAkhir, on_delete=models.CASCADE, related_name="milestone")
    template = models.ForeignKey(
        MilestoneTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    urutan = models.PositiveSmallIntegerField()
    nama = models.CharField(max_length=150)
    bobot = models.DecimalField(max_digits=5, decimal_places=2, help_text="Snapshot bobot template, persen.")
    target = models.DateField(null=True, blank=True)
    tingkat_penyelesaian = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(100)], help_text="0-100; dihitung hanya setelah diverifikasi."
    )
    diverifikasi_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    diverifikasi_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "milestone"
        verbose_name_plural = "milestone"
        ordering = ["urutan"]
        constraints = [
            models.UniqueConstraint(fields=["tugas_akhir", "urutan"], name="uniq_milestone_ta_urutan")
        ]

    def __str__(self):
        return f"TA#{self.tugas_akhir_id} {self.urutan}. {self.nama}"