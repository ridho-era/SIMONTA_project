from django.core.management.base import BaseCommand

from akademik.models import TugasAkhir
from notifikasi.services import sinkronkan_pengingat_ta


class Command(BaseCommand):
    help = "Membangun ulang jadwal pengingat untuk seluruh tugas akhir aktif."

    def handle(self, *args, **options):
        tugas_akhir = TugasAkhir.objects.filter(status=TugasAkhir.Status.AKTIF).order_by("pk")
        diproses = 0
        jadwal_baru = 0
        for item in tugas_akhir.iterator(chunk_size=200):
            jadwal_baru += sinkronkan_pengingat_ta(item.pk)
            diproses += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Sinkronisasi selesai: {diproses} tugas akhir aktif diperiksa; "
                f"{jadwal_baru} jadwal pengingat baru dibuat."
            )
        )
