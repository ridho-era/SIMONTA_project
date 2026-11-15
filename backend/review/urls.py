from django.urls import path

from .views import (
    DaftarReviewDosenView,
    DaftarReviewMahasiswaView,
    DetailReviewDosenView,
    DetailReviewMahasiswaView,
    DrafReviewDosenView,
    ItemChecklistMahasiswaView,
    ChecklistReviewMahasiswaView,
    TerbitkanReviewDosenView,
)

urlpatterns = [
    path("dosen/review/", DaftarReviewDosenView.as_view(), name="dosen-review-list"),
    path("dosen/review/<int:versi_id>/", DetailReviewDosenView.as_view(), name="dosen-review-detail"),
    path("dosen/review/<int:versi_id>/draf/", DrafReviewDosenView.as_view(), name="dosen-review-draf"),
    path("dosen/review/<int:review_id>/terbitkan/", TerbitkanReviewDosenView.as_view(), name="dosen-review-terbitkan"),
    path("mahasiswa/review/", DaftarReviewMahasiswaView.as_view(), name="mahasiswa-review-list"),
    path("mahasiswa/review/<int:review_id>/", DetailReviewMahasiswaView.as_view(), name="mahasiswa-review-detail"),
    path("mahasiswa/review/<int:review_id>/checklist/", ChecklistReviewMahasiswaView.as_view(), name="mahasiswa-review-checklist"),
    path("mahasiswa/checklist/<int:checklist_id>/", ItemChecklistMahasiswaView.as_view(), name="mahasiswa-checklist-detail"),
]
