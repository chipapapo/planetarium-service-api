from django.contrib import admin

from planetarium_service.models import (
    AstronomyShow,
    PlanetariumDome,
    Reservation,
    ShowSession,
    ShowTheme,
    Ticket
)

admin.site.register(PlanetariumDome)
admin.site.register(ShowTheme)
admin.site.register(AstronomyShow)
admin.site.register(ShowSession)
admin.site.register(Reservation)
admin.site.register(Ticket)
