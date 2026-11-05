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
    path(
        "recommendations/feedback",
        views.recommendations_feedback,
        name="recommendations-feedback",
    ),
    path("recommendations/click", views.recommendation_click, name="recommendations-click"),
    path("taste/pair", views.taste_pair, name="taste-pair"),
    path("taste/pair/submit", views.taste_pair_submit, name="taste-pair-submit"),
    path("taste/pairs", views.taste_pairs, name="taste-pairs"),
    path("taste/similar/<str:kind>/<int:pk>", views.similar_titles, name="taste-similar"),
]

