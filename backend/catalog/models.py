from django.conf import settings as django_settings
from django.db import models

try:
    from pgvector.django import VectorField

    HAS_PGVECTOR_LIB = True
except Exception:
    VectorField = None
    HAS_PGVECTOR_LIB = False

# The python lib alone is not enough: the pgvector server extension decides
# the real column type. The settings flag keeps model, migrations and DB in
# lockstep (see catalog.migrations.0008 for the upgrade path).
HAS_PGVECTOR = HAS_PGVECTOR_LIB and django_settings.PGVECTOR_ENABLED


def embedding_field():
    """vector(384) under pgvector; plain JSON list storage otherwise."""
    if HAS_PGVECTOR:
        return VectorField(dimensions=384, null=True, blank=True)
    return models.JSONField(null=True, blank=True)


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
    director = models.CharField(max_length=300, blank=True)
    cast = models.JSONField(default=list, blank=True)
    writers = models.JSONField(default=list, blank=True)
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)
    # Semantic embedding for similarity (pgvector when the stack is enabled)
    embedding = embedding_field()
    embedding_model = models.CharField(max_length=100, blank=True)
    embedding_updated_at = models.DateTimeField(null=True, blank=True)
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
    created_by = models.CharField(max_length=500, blank=True)
    cast = models.JSONField(default=list, blank=True)
    tagline = models.CharField(max_length=500, blank=True)
    vote_average = models.FloatField(null=True, blank=True)
    vote_count = models.PositiveIntegerField(null=True, blank=True)
    award_label = models.CharField(max_length=200, blank=True, db_index=True)
    genres = models.ManyToManyField(Genre, related_name="shows", blank=True)
    embedding = embedding_field()
    embedding_model = models.CharField(max_length=100, blank=True)
    embedding_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.name} ({self.release_year})"
