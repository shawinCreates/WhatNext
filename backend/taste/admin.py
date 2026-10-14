from django.contrib import admin

from .models import MovieFeature, UserPreference


@admin.register(MovieFeature)
class MovieFeatureAdmin(admin.ModelAdmin):
    list_display = ("movie", "show", "feature_key", "value", "source")
    list_filter = ("source", "feature_key")


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "feature_key", "polarity", "weight", "updated_at")
    list_filter = ("user", "polarity")
