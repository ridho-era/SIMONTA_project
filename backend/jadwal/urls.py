from django.urls import path

from .views import (
    MahasiswaJadwalView,
    PermohonanMasukDosenView,
    RescheduleMahasiswaView,
    SetujuiJadwalView,
    TolakJadwalView,
    UsulkanWaktuJadwalView,
)

urlpatterns = [
    path("mahasiswa/jadwal/", MahasiswaJadwalView.as_view(), name="mahasiswa-jadwal"),
    path("mahasiswa/jadwal/<int:pk>/reschedule/", RescheduleMahasiswaView.as_view(), name="mahasiswa-jadwal-reschedule"),
    path("dosen/jadwal/permohonan/", PermohonanMasukDosenView.as_view(), name="dosen-jadwal-permohonan"),
    path("dosen/jadwal/<int:pk>/setujui/", SetujuiJadwalView.as_view(), name="dosen-jadwal-setujui"),
    path("dosen/jadwal/<int:pk>/tolak/", TolakJadwalView.as_view(), name="dosen-jadwal-tolak"),
    path("dosen/jadwal/<int:pk>/usulkan/", UsulkanWaktuJadwalView.as_view(), name="dosen-jadwal-usulkan"),
]
