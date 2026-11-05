"""Backfill cast/writers/director/created_by from TMDB credits for Movies and Shows."""

from django.core.management.base import BaseCommand

from catalog.models import Movie, Show
from catalog.services import credits


class Command(BaseCommand):
    help = "Backfill cast/writers/director/created_by from TMDB credits."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="cap per run")
        parser.add_argument("--movies-only", action="store_true")
        parser.add_argument("--shows-only", action="store_true")

    def handle(self, *args, **opts):
        done = 0
        skipped = 0
        if not opts["shows_only"]:
            qs = Movie.objects.all().order_by("id")
            if opts["limit"]:
                qs = qs[: opts["limit"]]
            for movie in qs:
                try:
                    payload = credits("movie", movie.tmdb_id)
                except Exception:
                    skipped += 1
                    continue
                crew = payload.get("crew", []) or []
                cast = payload.get("cast", []) or []
                director_name = next((c.get("name", "") for c in crew if c.get("job") == "Director"), "") or movie.director
                writers = []
                for c in crew:
                    job = (c.get("job") or "").lower()
                    if job in ("writer", "screenplay", "story", "teleplay", "author"):
                        name = c.get("name")
                        if name and name not in writers:
                            writers.append(name)
                top_cast = []
                for c in cast[:10]:
                    name = c.get("name")
                    if name:
                        top_cast.append(name)
                updates = {}
                if director_name and director_name != movie.director:
                    updates["director"] = director_name[:300]
                if writers and getattr(movie, "writers", None) != writers:
                    updates["writers"] = writers
                if top_cast and getattr(movie, "cast", None) != top_cast:
                    updates["cast"] = top_cast
                if updates:
                    Movie.objects.filter(pk=movie.pk).update(**updates)
                    done += 1
                else:
                    skipped += 1
        if not opts["movies_only"]:
            qs = Show.objects.all().order_by("id")
            if opts["limit"]:
                qs = qs[: opts["limit"]]
            for show in qs:
                try:
                    payload = credits("tv", show.tmdb_id)
                except Exception:
                    skipped += 1
                    continue
                crew = payload.get("crew", []) or []
                cast = payload.get("cast", []) or []
                creators = payload.get("created_by", []) or []
                if creators and not show.created_by:
                    names = [c.get("name") for c in creators if c.get("name")]
                    if names:
                        Show.objects.filter(pk=show.pk).update(created_by=", ".join(names)[:500])
                top_cast = []
                for c in cast[:10]:
                    name = c.get("name")
                    if name:
                        top_cast.append(name)
                if top_cast and getattr(show, "cast", None) != top_cast:
                    Show.objects.filter(pk=show.pk).update(cast=top_cast)
                    done += 1
                else:
                    skipped += 1
        self.stdout.write(f"credits backfilled done={done} skipped={skipped}")
