from rest_framework import serializers

from catalog.models import Movie, Show
from catalog.serializers import MovieSerializer, ShowSerializer

from .models import UserMovie, UserShow


class UserMovieSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    movie_id = serializers.PrimaryKeyRelatedField(
        queryset=Movie.objects.all(), source="movie", write_only=True
    )

    class Meta:
        model = UserMovie
        fields = [
            "id",
            "movie",
            "movie_id",
            "status",
            "rating",
            "watched_at",
            "rewatched_count",
            "personal_note",
            "is_favorite",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []


class UserShowSerializer(serializers.ModelSerializer):
    show = ShowSerializer(read_only=True)
    show_id = serializers.PrimaryKeyRelatedField(
        queryset=Show.objects.all(), source="show", write_only=True
    )

    class Meta:
        model = UserShow
        fields = [
            "id",
            "show",
            "show_id",
            "status",
            "rating",
            "watched_at",
            "rewatched_count",
            "personal_note",
            "is_favorite",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []
