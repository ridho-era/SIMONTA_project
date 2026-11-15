from django.urls import path

from .views import (
    DaftarNotifikasiView,
    JumlahBelumDibacaView,
    PengaturanNotifikasiView,
    PratinjauPengingatView,
    PulihkanDefaultNotifikasiView,
    TandaiNotifikasiDibacaView,
    TandaiSemuaDibacaView,
)

urlpatterns = [
    path("notifikasi/", DaftarNotifikasiView.as_view(), name="notifikasi-daftar"),
    path("notifikasi/jumlah-belum-dibaca/", JumlahBelumDibacaView.as_view(), name="notifikasi-jumlah-belum-dibaca"),
    path("notifikasi/<int:pk>/dibaca/", TandaiNotifikasiDibacaView.as_view(), name="notifikasi-dibaca"),
    path("notifikasi/dibaca-semua/", TandaiSemuaDibacaView.as_view(), name="notifikasi-dibaca-semua"),
    path("notifikasi/pengaturan/", PengaturanNotifikasiView.as_view(), name="notifikasi-pengaturan"),
    path("notifikasi/pengaturan/pulihkan-default/", PulihkanDefaultNotifikasiView.as_view(), name="notifikasi-pengaturan-default"),
    path("notifikasi/pratinjau-pengingat/", PratinjauPengingatView.as_view(), name="notifikasi-pratinjau-pengingat"),
]
