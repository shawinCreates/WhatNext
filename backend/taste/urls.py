from django.urls import path

from . import views

urlpatterns = [
    path("taste/profile", views.taste_profile, name="taste-profile"),
    path("recommendations", views.recommendations, name="recommendations"),
    path(
        "recommendations/refresh",
        views.recommendations_refresh,
        name="recommendations-refresh",
    ),
]
