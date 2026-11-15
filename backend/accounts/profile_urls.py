from django.urls import path

from .views import FotoProfilView, LogoutOtherSessionsView, ProfilView

urlpatterns = [
    path("", ProfilView.as_view(), name="profil-saya"),
    path("foto/", FotoProfilView.as_view(), name="foto-profil"),
    path("sesi/keluar-perangkat-lain/", LogoutOtherSessionsView.as_view(), name="keluar-perangkat-lain"),
]
