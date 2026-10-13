from django.contrib import admin

from .models import Genre, Movie, Show


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "tmdb_id")
    search_fields = ("name",)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "release_year", "tmdb_id", "imdb_id")
    search_fields = ("title", "original_title", "tmdb_id", "imdb_id")
    list_filter = ("genres", "original_language")
    filter_horizontal = ("genres",)


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ("name", "release_year", "tmdb_id", "is_anime")
    search_fields = ("name", "original_name", "tmdb_id")
    list_filter = ("is_anime", "genres", "original_language")
    filter_horizontal = ("genres",)
