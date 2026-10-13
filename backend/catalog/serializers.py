from rest_framework import serializers

from .models import Genre, Movie, Show


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "tmdb_id", "name"]


class MovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = [
            "id",
            "tmdb_id",
            "imdb_id",
            "title",
            "original_title",
            "release_date",
            "release_year",
            "runtime",
            "overview",
            "original_language",
            "poster_path",
            "backdrop_path",
            "tagline",
            "vote_average",
            "vote_count",
            "award_label",
            "genres",
        ]


class ImportMovieSerializer(serializers.Serializer):
    tmdb_id = serializers.IntegerField()


class ShowSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Show
        fields = [
            "id",
            "tmdb_id",
            "name",
            "original_name",
            "first_air_date",
            "release_year",
            "overview",
            "original_language",
            "poster_path",
            "backdrop_path",
            "seasons",
            "episodes",
            "is_anime",
            "tagline",
            "vote_average",
            "vote_count",
            "award_label",
            "genres",
        ]
