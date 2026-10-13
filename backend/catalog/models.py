from django.db import models


class Genre(models.Model):
    tmdb_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Movie(models.Model):
    tmdb_id = models.PositiveIntegerField(unique=True)
    imdb_id = models.CharField(max_length=20, null=True, blank=True, unique=True)
    title = models.CharField(max_length=500)
    original_title = models.CharField(max_length=500, blank=True)
    release_date = models.DateField(null=True, blank=True)
    release_year = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    runtime = models.PositiveIntegerField(null=True, blank=True)
    overview = models.TextField(blank=True)
    original_language = models.CharField(max_length=10, blank=True)
    poster_path = models.CharField(max_length=255, blank=True)
    backdrop_path = models.CharField(max_length=255, blank=True)
    tagline = models.CharField(max_length=500, blank=True)
    vote_average = models.FloatField(null=True, blank=True)
    vote_count = models.PositiveIntegerField(null=True, blank=True)
    award_label = models.CharField(max_length=200, blank=True, db_index=True)
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [models.Index(fields=["title"])]

    def __str__(self):
        return f"{self.title} ({self.release_year})"


class Show(models.Model):
    """TV series and anime (TMDB TV entries; anime auto-flagged on import)."""

    tmdb_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=500)
    original_name = models.CharField(max_length=500, blank=True)
    first_air_date = models.DateField(null=True, blank=True)
    release_year = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    overview = models.TextField(blank=True)
    original_language = models.CharField(max_length=10, blank=True)
    poster_path = models.CharField(max_length=255, blank=True)
    backdrop_path = models.CharField(max_length=255, blank=True)
    seasons = models.PositiveIntegerField(null=True, blank=True)
    episodes = models.PositiveIntegerField(null=True, blank=True)
    is_anime = models.BooleanField(default=False, db_index=True)
    tagline = models.CharField(max_length=500, blank=True)
    vote_average = models.FloatField(null=True, blank=True)
    vote_count = models.PositiveIntegerField(null=True, blank=True)
    award_label = models.CharField(max_length=200, blank=True, db_index=True)
    genres = models.ManyToManyField(Genre, related_name="shows", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.name} ({self.release_year})"
