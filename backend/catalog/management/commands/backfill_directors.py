"""One-off: fetch TMDB credits for every Movie with a blank director field."""

from django.core.management.base import BaseCommand

from catalog.models import Movie
from catalog.services import director_of


class Command(BaseCommand):
    help = "Backfill Movie.director from TMDB credits for existing titles."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="cap per run")

    def handle(self, *args, **opts):
        missing = Movie.objects.filter(director="").order_by("id")
        if opts["limit"]:
            missing = missing[: opts["limit"]]
        done, skipped = 0, 0
        for movie in missing:
            name = director_of("movie", movie.tmdb_id)
            if name:
                Movie.objects.filter(pk=movie.pk).update(director=name)
                done += 1
            else:
                skipped += 1
        self.stdout.write(
            f"directors backfilled={done} skipped={skipped} "
            f"(still blank: {Movie.objects.filter(director='').count()})"
        )