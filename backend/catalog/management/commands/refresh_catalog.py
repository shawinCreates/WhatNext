"""Refresh the local catalog with fresh TMDB picks that are not in it yet.

Imports trending + top-rated movies and shows you don't already have as
*catalog candidates* — they never enter the library, they just widen the
recommendation pool past whatever you happen to have imported so far.
"""

from django.core.management.base import BaseCommand

from taste.services import backfill_title

from catalog import services


MOVIE_SECTIONS = ("trending", "top_rated")
SHOW_SECTIONS = ("trending", "top_rated")


class Command(BaseCommand):
    help = "Top up the catalog with ~40 unseen movies + ~40 unseen shows."

    def add_arguments(self, parser):
        parser.add_argument("--movie-limit", type=int, default=40)
        parser.add_argument("--show-limit", type=int, default=40)

    def handle(self, *args, **opts):
        for media, sections, limit in (
            ("movie", MOVIE_SECTIONS, opts["movie_limit"]),
            ("show", SHOW_SECTIONS, opts["show_limit"]),
        ):
            added, seen_ids = 0, set()
            for section in sections:
                if added >= limit:
                    break
                fetch = services.movie_section if media == "movie" else services.show_section
                try:
                    payload = fetch(section)
                except services.TMDBError as exc:
                    self.stderr.write(f"{section}/{media} fetch failed: {exc}")
                    continue
                results = payload.get("results", []) if isinstance(payload, dict) else payload
                for item in results:
                    if added >= limit:
                        break
                    tmdb_id = item["id"]
                    if tmdb_id in seen_ids or self._exists(media, tmdb_id):
                        continue
                    seen_ids.add(tmdb_id)
                    if self._import(media, tmdb_id):
                        added += 1
            self.stdout.write(f"{media}: +{added}")
        self.stdout.write("catalog refreshed.")

    def _exists(self, media, tmdb_id):
        model = services.Movie if media == "movie" else services.Show
        return model.objects.filter(tmdb_id=tmdb_id).exists()

    def _import(self, media, tmdb_id):
        """Fetch details (+ movie director), upsert, build features."""
        details = services.get_movie if media == "movie" else services.get_show
        try:
            payload = details(tmdb_id)
            if media == "movie":
                movie = services.upsert_movie(
                    payload, director=services.director_of("movie", tmdb_id)
                )
                backfill_title(movie=movie)
            else:
                show = services.upsert_show(payload)
                backfill_title(show=show)
            return True
        except services.TMDBError as exc:
            self.stderr.write(f"{media}/{tmdb_id} import failed: {exc}")
            return False