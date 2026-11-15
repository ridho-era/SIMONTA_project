from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="docs",
    ),
    path("api/v1/", include("core.urls")),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/profil/", include("accounts.profile_urls")),
    path("api/v1/periode/", include("akademik.urls")),
    path("api/v1/", include("milestone.urls")),
    path("api/v1/", include("dokumen.urls")),
    path("api/v1/", include("review.urls")),
    path("api/v1/", include("dashboard.urls")),
    path("api/v1/", include("jadwal.urls")),
    path("api/v1/", include("pesan.urls")),
    path("api/v1/", include("notifikasi.urls")),
    path("api/v1/", include("keterlambatan.urls")),
]