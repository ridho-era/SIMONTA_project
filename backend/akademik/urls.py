from django.urls import path

from .views import PeriodeAktifView

urlpatterns = [
    path("aktif/", PeriodeAktifView.as_view(), name="periode-aktif"),
]