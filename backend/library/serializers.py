from rest_framework import serializers

from catalog.models import Movie, Show
from catalog.serializers import MovieSerializer, ShowSerializer

from .models import UserMovie, UserShow


class UserMovieSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    movie_id = serializers.PrimaryKeyRelatedField(
        queryset=Movie.objects.all(), source="movie", write_only=True
    )

    def validate_rating(self, value):
        if value is None:
            return None
        try:
            rounded = round(float(value), 1)
        except (TypeError, ValueError):
            raise serializers.ValidationError("rating must be a number")
        if not 1 <= rounded <= 10:
            raise serializers.ValidationError("rating must be between 1 and 10")
        return rounded

    def validate_personal_note(self, value):
        note = value.strip()
        if len(note) > 2000:
            raise serializers.ValidationError("note must be 2000 characters or fewer")
        return note

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

    def validate_rating(self, value):
        if value is None:
            return None
        try:
            rounded = round(float(value), 1)
        except (TypeError, ValueError):
            raise serializers.ValidationError("rating must be a number")
        if not 1 <= rounded <= 10:
            raise serializers.ValidationError("rating must be between 1 and 10")
        return rounded

    def validate_personal_note(self, value):
        note = value.strip()
        if len(note) > 2000:
            raise serializers.ValidationError("note must be 2000 characters or fewer")
        return note

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
