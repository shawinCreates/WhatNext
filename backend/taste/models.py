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


class RecoServe(models.Model):
    """One recommendation shown to a user; powers the "never the same picks" rotation."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reco_serves",
    )
    tkey = models.CharField(max_length=20)  # 'm<id>' / 's<id>' like reco keys
    served_at = models.DateTimeField(auto_now_add=True)
    algorithm_version = models.CharField(max_length=50, blank=True)
    feature_version = models.CharField(max_length=50, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "served_at"])]

    def __str__(self):
        return f"{self.user} served {self.tkey} at {self.served_at:%Y-%m-%d %H:%M}"


class RecoImpression(models.Model):
    """Track individual recommendation impressions/clicks for learning loop."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reco_impressions"
    )
    tkey = models.CharField(max_length=20)
    kind = models.CharField(max_length=10, blank=True)
    title_id = models.IntegerField(null=True, blank=True)
    position = models.IntegerField(null=True, blank=True)
    clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)
    impression_at = models.DateTimeField(auto_now_add=True)
    algorithm_version = models.CharField(max_length=50, blank=True)
    feature_version = models.CharField(max_length=50, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "impression_at"]),
            models.Index(fields=["user", "tkey"]),
        ]

    def __str__(self):
        return f"{self.user} {self.tkey} clicked={self.clicked}"


class PairwiseComparison(models.Model):
    """Explicit A-over-B preference signal (V1 pairwise comparisons).

    tkey_a/tkey_b are stored in normalized order (tkey_a < tkey_b) so the same
    pair can't be duplicated regardless of presentation order. winner_tkey is
    tkey_a, tkey_b, or 'tie'.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pairwise_comparisons",
    )
    tkey_a = models.CharField(max_length=20)  # 'm<id>' / 's<id>'
    tkey_b = models.CharField(max_length=20)
    winner_tkey = models.CharField(max_length=20)  # tkey_a, tkey_b, 'tie', or 'neither'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["user", "winner_tkey"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tkey_a", "tkey_b"], name="unique_user_pair"
            ),
            models.CheckConstraint(
                name="pairwise_winner_is_a_b_or_tie",
                condition=(
                    models.Q(winner_tkey=models.F("tkey_a"))
                    | models.Q(winner_tkey=models.F("tkey_b"))
                    | models.Q(winner_tkey="tie")
                    | models.Q(winner_tkey="neither")
                ),
            ),
        ]

    def __str__(self):
        return f"{self.user} {self.tkey_a} vs {self.tkey_b} -> {self.winner_tkey}"


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

