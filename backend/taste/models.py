from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from catalog.models import Movie, Show


class MovieFeature(models.Model):
    """One taste-dimension value for a catalog title (movie or show)."""

    SOURCES = (("heuristic", "Heuristic"), ("llm", "LLM"), ("manual", "Manual"))

    movie = models.ForeignKey(
        Movie, null=True, blank=True, on_delete=models.CASCADE, related_name="features"
    )
    show = models.ForeignKey(
        Show, null=True, blank=True, on_delete=models.CASCADE, related_name="features"
    )
    feature_key = models.CharField(max_length=50, db_index=True)
    value = models.FloatField()
    confidence = models.FloatField(default=0.5)
    source = models.CharField(max_length=20, choices=SOURCES, default="heuristic")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["movie", "feature_key"], name="unique_movie_feature"
            ),
            models.UniqueConstraint(
                fields=["show", "feature_key"], name="unique_show_feature"
            ),
        ]

    def clean(self):
        if bool(self.movie_id) == bool(self.show_id):
            raise ValidationError("feature needs exactly one of movie, show")

    def __str__(self):
        title = self.movie or self.show
        return f"{title} [{self.feature_key}={self.value}]"


class UserPreference(models.Model):
    """One aggregated taste dimension for a user (see 04-database-model §6)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="taste_preferences",
    )
    feature_key = models.CharField(max_length=50, db_index=True)
    polarity = models.SmallIntegerField(choices=((1, "Positive"), (-1, "Negative")))
    weight = models.FloatField()
    confidence = models.FloatField(default=0.5)
    source = models.CharField(max_length=20, default="ratings")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "feature_key"], name="unique_user_preference"
            ),
        ]
        indexes = [models.Index(fields=["user", "feature_key"])]

    def __str__(self):
        sign = "+" if self.polarity > 0 else "-"
        return f"{self.user} {sign}{self.feature_key} ({self.weight:.2f})"
