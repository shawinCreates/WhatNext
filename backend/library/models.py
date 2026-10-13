from django.conf import settings
from django.db import models

from catalog.models import Movie, Show


class LibraryStatus(models.TextChoices):
    WATCHLIST = "WATCHLIST", "Watchlist"
    WATCHED = "WATCHED", "Watched"
    REJECTED = "REJECTED", "Rejected"
    SKIPPED = "SKIPPED", "Skipped"


class UserMovie(models.Model):
    Status = LibraryStatus

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="library"
    )
    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="library_entries"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WATCHLIST
    )
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    watched_at = models.DateTimeField(null=True, blank=True)
    rewatched_count = models.PositiveSmallIntegerField(default=0)
    personal_note = models.TextField(blank=True)
    is_favorite = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "movie"], name="unique_user_movie"),
        ]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.movie} [{self.status}]"


class UserShow(models.Model):
    Status = LibraryStatus

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="show_library"
    )
    show = models.ForeignKey(
        Show, on_delete=models.CASCADE, related_name="library_entries"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WATCHLIST
    )
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    watched_at = models.DateTimeField(null=True, blank=True)
    rewatched_count = models.PositiveSmallIntegerField(default=0)
    personal_note = models.TextField(blank=True)
    is_favorite = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "show"], name="unique_user_show"),
        ]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.show} [{self.status}]"
