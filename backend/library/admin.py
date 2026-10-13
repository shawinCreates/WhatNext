from django.contrib import admin

from .models import UserMovie, UserShow


@admin.register(UserMovie)
class UserMovieAdmin(admin.ModelAdmin):
    list_display = ("movie", "user", "status", "rating", "updated_at")
    list_filter = ("status", "user")
    search_fields = ("movie__title",)
    autocomplete_fields = ("movie",)


@admin.register(UserShow)
class UserShowAdmin(admin.ModelAdmin):
    list_display = ("show", "user", "status", "rating", "updated_at")
    list_filter = ("status", "user")
    search_fields = ("show__name",)
    autocomplete_fields = ("show",)
