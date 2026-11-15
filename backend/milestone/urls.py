from django.urls import path

from .views import MahasiswaMilestoneView, TargetView, VerifikasiView

urlpatterns = [
    path("mahasiswa/milestone/", MahasiswaMilestoneView.as_view(), name="mahasiswa-milestone"),
    path("dosen/milestone/<int:pk>/target/", TargetView.as_view(), name="dosen-milestone-target"),
    path("dosen/milestone/<int:pk>/verifikasi/", VerifikasiView.as_view(), name="dosen-milestone-verifikasi"),
]