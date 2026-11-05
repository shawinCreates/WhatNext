"""Broaden the catalog with TMDB /discover windows: genre x decade.

Taste crawling (crawl_taste) only reaches titles TMDB considers relevant to
titles you already love. This command walks the *whole* genre map instead —
every genre x decade window at a vote-quality floor, alternating popularity-
and rating-sorted pages so underrated back-catalogue titles surface alongside
blockbusters. Imported titles are candidates (never in the library), with
taste features backfilled at import.

Reruns are safe: upserts are keyed by tmdb_id and existing titles never
consume import budget.
"""

import time

from django.core.management.base import BaseCommand

from catalog import services
from catalog.ingest import import_title
from catalog.models import Movie, Show

DECADES_DEFAULT = (1970, 1980, 1990, 2000, 2010, 2020)
SORTS = ("popularity.desc", "vote_average.desc")
# vote_average windows need their own quality floor or junk with 5 votes and
# a 9.5 average sneaks in (same guard movie_section/awarded uses).
AVG_FLOORS = {"movie": 7.0, "show": 7.5}
TMDB_MEDIA = {"movie": "movie", "show": "tv"}


class Command(BaseCommand):
    help = (
        "Sweep TMDB discover breadth: every genre x decade window above a "
        "vote-quality floor, alternating popularity/rating sorts."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--media", default="movie,show", help="comma list: movie, show"
        )
        parser.add_argument(
            "--genres",
            default="",
            help="optional comma list of TMDB genre names to restrict windows (default: all)",
        )
        parser.add_argument(
            "--decades",
            default=",".join(str(d) for d in DECADES_DEFAULT),
            help="comma list of decade starts, e.g. 1980,1990",
        )
        parser.add_argument(
            "--pages-per-window",
            type=int,
            default=2,
            help="discover pages per window (20 titles/page each)",
        )
        parser.add_argument(
            "--min-votes-movie", type=int, default=300, help="vote floor for movies"
        )
        parser.add_argument(
            "--min-votes-show", type=int, default=100, help="vote floor for shows"
        )
        parser.add_argument(
            "--language",
            default="",
            help="optional with_original_language filter, e.g. ja for anime-heavy splits",
        )
        parser.add_argument(
            "--max-imports",
            type=int,
            default=500,
            help="import cap per run (0 = unlimited); rerun continues with a fresh sweep",
        )
        parser.add_argument("--sleep", type=float, default=0.25, help="pause between TMDB calls (s)")

    def handle(self, *args, **opts):
        kinds = [k.strip() for k in opts["media"].split(",") if k.strip() in TMDB_MEDIA]
        if not kinds:
            self.stderr.write("--media must contain movie and/or show")
            return
        sleep = max(0.0, opts["sleep"])
        remaining = {"n": opts["max_imports"] if opts["max_imports"] > 0 else 10**9}
        self.floors = {
            "movie": opts["min_votes_movie"],
            "show": opts["min_votes_show"],
        }
        self.movie_ids = set(Movie.objects.values_list("tmdb_id", flat=True))
        self.show_ids = set(Show.objects.values_list("tmdb_id", flat=True))
        self.attempted = set()
        stats = {
            "pages": 0,
            "candidates": 0,
            "imported": 0,
            "existing": 0,
            "below_floor": 0,
            "errors": 0,
        }

        windows = []
        for kind in kinds:
            try:
                genre_rows = services.genre_list(TMDB_MEDIA[kind])
            except services.TMDBError as exc:
                self.stderr.write(f"genre list for {kind} failed: {exc}")
                continue
            for decade in self._decades(opts["decades"]):
                for genre in self._genre_filter(genre_rows, opts["genres"]):
                    windows.append((kind, genre, decade))

        if not windows:
            self.stdout.write("no discover windows to sweep (genre filter too narrow?)")
            return

        total_pages = max(0, opts["pages_per_window"])
        pointers = [0] * len(windows)
        while remaining["n"] > 0 and any(p < total_pages for p in pointers):
            for wi, (kind, genre, decade) in enumerate(windows):
                if pointers[wi] >= total_pages or remaining["n"] <= 0:
                    continue
                pointers[wi] += 1
                params = {
                    "with_genres": genre["id"],
                    "vote_count_gte": self.floors[kind],
                    "page": pointers[wi],
                }
                if wi % len(SORTS) == 0:
                    params["sort_by"] = "popularity.desc"
                else:
                    params["sort_by"] = "vote_average.desc"
                    params["vote_average_gte"] = AVG_FLOORS[kind]
                if opts["language"]:
                    params["with_original_language"] = opts["language"]
                params.update(self._date_range(kind, decade))
                self._pause(sleep)
                try:
                    results = services.discover(TMDB_MEDIA[kind], **params)
                    stats["pages"] += 1
                except services.TMDBError as exc:
                    self.stderr.write(
                        f"discover {genre['name']} {decade}s p{pointers[wi]} failed: {exc}"
                    )
                    continue
                for item in results:
                    if remaining["n"] <= 0:
                        break
                    self._import_candidate(kind, genre, decade, item, remaining, stats)

        self.stdout.write(
            f"windows={len(windows)} pages-per-window={total_pages} "
            f"pages-fetched={stats['pages']} "
            f"candidates={stats['candidates']} imported={stats['imported']} "
            f"existing={stats['existing']} below-floor={stats['below_floor']} "
            f"errors={stats['errors']} "
            f"budget-left={remaining['n'] if remaining['n'] < 10**9 else 'uncapped'}"
        )
        if remaining["n"] <= 0:
            self.stdout.write("--max-imports cut this run; rerun resumes (existing skips).")

    # --- helpers -----------------------------------------------------------

    def _decades(self, raw):
        out = []
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if chunk.isdigit():
                out.append(int(chunk) - int(chunk) % 10)
        return out or list(DECADES_DEFAULT)

    def _genre_filter(self, genre_rows, wanted):
        if not wanted:
            return genre_rows
        names = {g.strip().lower() for g in wanted.split(",") if g.strip()}
        return [g for g in genre_rows if g.get("name", "").lower() in names]

    def _date_range(self, kind, decade):
        field = "primary_release_date" if kind == "movie" else "first_air_date"
        return {f"{field}.gte": f"{decade}-01-01", f"{field}.lte": f"{decade}-12-31"}

    def _import_candidate(self, kind, genre, decade, item, remaining, stats):
        """Window result → catalog candidate; budget is only consumed when a
        details call is actually made (existing ids skip locally)."""
        tmdb_id = item["id"]
        if (kind, tmdb_id) in self.attempted:
            return
        self.attempted.add((kind, tmdb_id))
        existing = self.movie_ids if kind == "movie" else self.show_ids
        if tmdb_id in existing:
            stats["existing"] += 1
            return
        stats["candidates"] += 1
        if (item.get("vote_count") or 0) < self.floors[kind]:
            stats["below_floor"] += 1
            return
        name = item.get("title") or item.get("name") or f"tmdb:{tmdb_id}"
        remaining["n"] -= 1
        try:
            _obj, imported_now = import_title(kind, tmdb_id)
        except services.TMDBError as exc:
            stats["errors"] += 1
            self.stderr.write(f"{kind}/{tmdb_id} import failed: {exc}")
            return
        if not imported_now:
            stats["existing"] += 1
            return
        existing.add(tmdb_id)
        stats["imported"] += 1
        if stats["imported"] % 25 == 0:
            self.stdout.write(f"  imported {stats['imported']} so far...")
        self.stdout.write(f"  + {name} [{genre['name']} {decade}s]")

    def _pause(self, seconds):
        if seconds > 0:
            time.sleep(seconds)
