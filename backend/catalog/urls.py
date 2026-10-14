from django.urls import path

from . import views

urlpatterns = [
    path("movies", views.movies_list, name="movie-list"),
    path("movies/search", views.search, name="movie-search"),
    path("movies/trending", views.trending, name="movie-trending"),
    path("movies/browse", views.movies_browse, name="movie-browse"),
    path("movies/import", views.import_movie, name="movie-import"),
    path("movies/<int:pk>", views.movie_detail, name="movie-detail"),
    path("shows", views.shows_list, name="show-list"),
    path("shows/search", views.shows_search, name="show-search"),
    path("shows/browse", views.shows_browse, name="show-browse"),
    path("shows/import", views.import_show, name="show-import"),
    path("shows/<int:pk>", views.show_detail, name="show-detail"),
    path("anime/browse", views.anime_browse, name="anime-browse"),
    path("genres", views.genres, name="genre-list"),
    path("tmdb/<str:media>/<tmdb_id>/videos", views.title_videos, name="title-videos"),
    path("tmdb/<str:media>/<tmdb_id>/credits", views.title_credits, name="title-credits"),
    path("tmdb/<str:media>/<tmdb_id>/similar", views.title_similar, name="title-similar"),
    path("tmdb/tv/<int:tmdb_id>/season/<int:season>", views.tv_season, name="tv-season"),
]
