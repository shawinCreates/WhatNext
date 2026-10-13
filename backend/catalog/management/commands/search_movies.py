from django.core.management.base import BaseCommand, CommandError

from catalog.services import TMDBError, search_movies


class Command(BaseCommand):
    help = "Search TMDB for movies."

    def add_arguments(self, parser):
        parser.add_argument("query")

    def handle(self, *args, **options):
        try:
            results = search_movies(options["query"])
        except TMDBError as exc:
            raise CommandError(str(exc)) from exc
        for result in results:
            year = (result.get("release_date") or "????")[:4]
            self.stdout.write(f"{result['id']:>8}  {result['title']} ({year})")
