from django.core.management.base import BaseCommand, CommandError

from catalog.services import TMDBError, get_movie, upsert_movie


class Command(BaseCommand):
    help = "Import a movie from TMDB by its TMDB id."

    def add_arguments(self, parser):
        parser.add_argument("tmdb_id", type=int)

    def handle(self, *args, **options):
        try:
            payload = get_movie(options["tmdb_id"])
        except TMDBError as exc:
            raise CommandError(str(exc)) from exc
        movie = upsert_movie(payload)
        self.stdout.write(self.style.SUCCESS(f"Imported {movie}"))
