from django.urls import path

from .views import DashboardDosenView, DashboardMahasiswaView, DaftarMahasiswaBimbinganView

urlpatterns = [
    path("mahasiswa/dashboard/", DashboardMahasiswaView.as_view(), name="mahasiswa-dashboard"),
    path("dosen/dashboard/", DashboardDosenView.as_view(), name="dosen-dashboard"),
    path("dosen/mahasiswa/", DaftarMahasiswaBimbinganView.as_view(), name="dosen-mahasiswa-list"),
]
