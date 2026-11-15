from django.urls import path

from .views import (
    DosenCatatanAdministrasiView,
    DosenCatatanDetailView,
    DosenKeputusanCatatanView,
    DosenKeputusanKeberatanView,
    DosenKeterlambatanView,
    KeberatanBuktiView,
    MahasiswaDendaView,
    MahasiswaKeberatanView,
)

urlpatterns = [
    path("mahasiswa/denda/", MahasiswaDendaView.as_view(), name="mahasiswa-denda"),
    path(
        "mahasiswa/denda/<int:catatan_id>/keberatan/",
        MahasiswaKeberatanView.as_view(),
        name="mahasiswa-keberatan-denda",
    ),
    path("dosen/keterlambatan/", DosenKeterlambatanView.as_view(), name="dosen-keterlambatan"),
    path(
        "dosen/keterlambatan/administrasi/",
        DosenCatatanAdministrasiView.as_view(),
        name="dosen-catatan-administrasi",
    ),
    path(
        "dosen/keterlambatan/<int:catatan_id>/",
        DosenCatatanDetailView.as_view(),
        name="dosen-keterlambatan-detail",
    ),
    path(
        "dosen/keterlambatan/<int:catatan_id>/keputusan/",
        DosenKeputusanCatatanView.as_view(),
        name="dosen-keterlambatan-keputusan",
    ),
    path(
        "dosen/keberatan/<int:keberatan_id>/keputusan/",
        DosenKeputusanKeberatanView.as_view(),
        name="dosen-keberatan-keputusan",
    ),
    path("keberatan/<int:keberatan_id>/bukti/", KeberatanBuktiView.as_view(), name="keberatan-bukti"),
]
