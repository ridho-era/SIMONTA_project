from django.urls import path

from .views import (
    DaftarPercakapanView,
    KirimPesanView,
    TandaiDibacaView,
    ThreadPesanView,
    UnduhLampiranPesanView,
)

urlpatterns = [
    path("pesan/", DaftarPercakapanView.as_view(), name="pesan-daftar"),
    path("pesan/lampiran/<int:pk>/unduh/", UnduhLampiranPesanView.as_view(), name="pesan-lampiran-unduh"),
    path("pesan/<int:pk>/", ThreadPesanView.as_view(), name="pesan-thread"),
    path("pesan/<int:pk>/kirim/", KirimPesanView.as_view(), name="pesan-kirim"),
    path("pesan/<int:pk>/dibaca/", TandaiDibacaView.as_view(), name="pesan-dibaca"),
]
