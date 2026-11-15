from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone


def lockout_response(request, credentials=None, *args, **kwargs):
    """Respons saat akun+IP terkunci oleh django-axes (dipakai juga oleh view login)."""
    cooloff = getattr(settings, "AXES_COOLOFF_TIME", None)
    seconds = int(cooloff.total_seconds()) if cooloff else 900
    minutes = max(seconds // 60, 1)
    response = JsonResponse(
        {
            "detail": (
                "Terlalu banyak percobaan masuk yang gagal. "
                f"Coba lagi dalam {minutes} menit."
            )
        },
        status=429,
    )
    response["Retry-After"] = str(seconds)
    return response


def is_locked_out(request, identifier):
    """True bila kombinasi akun + IP sudah mencapai batas gagal dalam masa cooloff.

    Memeriksa catatan AccessAttempt milik django-axes secara langsung, sehingga
    penguncian tidak bergantung pada pemeriksaan di backend autentikasi.
    """
    from axes.helpers import get_client_ip_address
    from axes.models import AccessAttempt

    threshold = timezone.now() - settings.AXES_COOLOFF_TIME
    return AccessAttempt.objects.filter(
        username=identifier,
        ip_address=get_client_ip_address(request),
        failures_since_start__gte=settings.AXES_FAILURE_LIMIT,
        attempt_time__gte=threshold,
    ).exists()