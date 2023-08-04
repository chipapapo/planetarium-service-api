from django.urls import include, path
from rest_framework import routers

from planetarium_service.views import (
    AstronomyShowViewSet,
    PlanetariumDomeViewSet,
    ReservationViewSet,
    ShowSessionViewSet,
    ShowThemeViewSet
)

router = routers.DefaultRouter()
router.register("themes", ShowThemeViewSet)
router.register("planetarium_domes", PlanetariumDomeViewSet)
router.register("shows", AstronomyShowViewSet)
router.register("show_sessions", ShowSessionViewSet)
router.register("reservations", ReservationViewSet)

urlpatterns = [path("", include(router.urls))]

app_name = "planetarium_service"
