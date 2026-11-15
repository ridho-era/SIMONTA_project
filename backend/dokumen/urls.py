from django.urls import path

from .views import DokumenSayaView, PratinjauBerkasView, UnduhBerkasView

urlpatterns = [
    path("mahasiswa/dokumen/", DokumenSayaView.as_view(), name="mahasiswa-dokumen"),
    path("berkas/<int:pk>/unduh/", UnduhBerkasView.as_view(), name="berkas-unduh"),
    path("berkas/<int:pk>/pratinjau/", PratinjauBerkasView.as_view(), name="berkas-pratinjau"),
]