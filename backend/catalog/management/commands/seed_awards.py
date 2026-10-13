from django.core.management.base import BaseCommand, CommandError

from catalog.awards import AWARDED_MOVIES
from catalog.services import TMDBError, get_movie, upsert_movie


class Command(BaseCommand):
    help = "Seed the curated award-winners list (verifies each TMDB id)."

    def handle(self, *args, **options):
        ok, failed = 0, []
        for tmdb_id, label in AWARDED_MOVIES:
            try:
                movie = upsert_movie(get_movie(tmdb_id))
            except TMDBError as exc:
                failed.append((tmdb_id, str(exc)))
                continue
            if not movie.award_label:
                movie.award_label = label
                movie.save(update_fields=["award_label"])
            ok += 1
        for tmdb_id, error in failed:
            self.stderr.write(f"miss {tmdb_id}: {error}")
        if failed:
            raise CommandError(f"{len(failed)} award id(s) failed verification")
        self.stdout.write(self.style.SUCCESS(f"Seeded {ok} award winners"))
