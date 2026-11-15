from django.urls import path

from .views import HealthView, PusatBantuanView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("bantuan/", PusatBantuanView.as_view(), name="pusat-bantuan"),
]