from celery import shared_task

from .services import proses_keterlambatan_harian


@shared_task(name="keterlambatan.proses_keterlambatan_harian", ignore_result=False)
def proses_keterlambatan_harian_task():
    """Menilai tenggat revisi yang sudah terlewat setiap hari; aman dijalankan ulang."""
    return proses_keterlambatan_harian()
