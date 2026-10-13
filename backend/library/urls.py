from django.urls import path

from . import views

urlpatterns = [
    path("library", views.library, name="library"),
    path("library/items/<int:pk>", views.library_item, name="library-item"),
    path("library/shows", views.shows_library, name="shows-library"),
    path(
        "library/shows/items/<int:pk>",
        views.shows_library_item,
        name="shows-library-item",
    ),
]
