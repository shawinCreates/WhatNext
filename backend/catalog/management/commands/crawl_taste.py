"""Crawl TMDB outward from the titles you loved.

For every library entry rated >= --min-rating (or flagged favorite), pulls
TMDB /recommendations and /similar pages and imports the unseen titles as
catalog candidates — the recommendation pool grows exactly where your taste
lives, not where global popularity sits. --creators extends the same move to
people: filmographies of your loved movies' directors and TV creators.

Everything lands as *catalog candidates* (never in the library) and gets
taste features at import. Idempotent by design: existing tmdb_ids skip
(checked locally, no TMDB call), so a rerun after an --max-imports cutoff
continues the same crawl. Depth one per pass — newly imported titles are not
crawled themselves in the same run.
"""

import time
from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from catalog import services
from catalog.ingest import import_title
from catalog.models import Movie, Show
from library.models import UserMovie, UserShow

TMDB_MEDIA = {"movie": "movie", "show": "tv"}
# A seed stops paginating once this many floor-passing unseen candidates are
# in hand — recommendations pages for a loved title get redundant fast, and
# p1 of the next seed matters more than p4 of this one.
SOURCE_CANDIDATE_CAP = 12


class Command(BaseCommand):
    help = (
        "Grow the recommendation pool outward from loved titles: TMDB "
        "recommendations + similar (+ creator filmographies with --creators)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--user", default="", help="single-user app: first user by default")
        parser.add_argument(
            "--min-rating",
            type=float,
            default=8.0,
            help="ratings at or above this (or favorites) seed the crawl",
        )
        parser.add_argument("--pages", type=int, default=3, help="recommendation pages per liked title")
        parser.add_argument(
            "--similar-pages", type=int, default=1, help="similar pages per liked title"
        )
        parser.add_argument(
            "--min-votes-movie",
            type=int,
            default=20,
            help="TMDB vote floor for imported movies (quality gate)",
        )
        parser.add_argument(
            "--min-votes-show",
            type=int,
            default=5,
            help="TMDB vote floor for imported shows (quality gate)",
        )
        parser.add_argument(
            "--creators",
            action="store_true",
            help="also import filmographies of loved titles' directors/creators",
        )
        parser.add_argument(
            "--creator-captures",
            type=int,
            default=8,
            help="filmography imports per liked person (their highest-voted titles)",
        )
        parser.add_argument(
            "--seed-cap",
            type=int,
            default=0,
            help="crawl only the top N seeds (0 = all); useful for incremental runs",
        )
        parser.add_argument(
            "--max-imports",
            type=int,
            default=300,
            help="import cap per run (0 = unlimited); rerun to continue a cut crawl",
        )
        parser.add_argument("--sleep", type=float, default=0.25, help="pause between TMDB calls (s)")

    def handle(self, *args, **opts):
        user = self._user(opts["user"])
        sleep = max(0.0, opts["sleep"])
        stats = Counter()

        liked = self._liked(user, opts["min_rating"])
        if opts["seed_cap"] > 0:
            liked = liked[: opts["seed_cap"]]
        if not liked:
            self.stdout.write(
                "no seeded titles: rate something 8+ (or mark favorites) first."
            )
            return

        self.movie_ids = set(Movie.objects.values_list("tmdb_id", flat=True))
        self.show_ids = set(Show.objects.values_list("tmdb_id", flat=True))
        self.attempted = set()  # (kind, tmdb_id) already examined this run
        self.floors = {
            "movie": opts["min_votes_movie"],
            "show": opts["min_votes_show"],
        }

        remaining = self._remaining(opts["max_imports"])
        sources = self._harvest(liked, opts, stats, sleep)
        budget_capped = self._import_round_robin(sources, remaining, opts, stats)

        if opts["creators"] and remaining["n"] > 0:
            budget_capped = self._import_creators(
                liked, opts, stats, sleep, remaining
            ) or budget_capped

        self._report(stats, liked, sources, remaining)
        if remaining["n"] <= 0 or budget_capped:
            self.stdout.write(
                "--max-imports cut this run; rerun to continue (done titles skip)."
            )

    # --- seeding -----------------------------------------------------------

    def _user(self, name):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.get(username=name) if name else User.objects.first()
        if not user:
            raise CommandError("no user exists; create one first")
        return user

    def _liked(self, user, min_rating):
        """(kind, tmdb_id, label, rating, person_names) seeds, highest first.

        Rated entries at/above min_rating plus favorites. REJECTED entries
        never seed — a rejected title crawling recommendations would seed the
        pool with its neighbors, which is the opposite of what "not for me"
        meant.
        """
        out = []
        for entry in UserMovie.objects.filter(user=user).select_related("movie"):
            if entry.status == "REJECTED":
                continue
            if (entry.rating is not None and entry.rating >= min_rating) or entry.is_favorite:
                movie = entry.movie
                out.append(
                    (
                        "movie",
                        movie.tmdb_id,
                        f"{movie.title} ({movie.release_year})",
                        entry.rating,
                        movie.director or "",
                    )
                )
        for entry in UserShow.objects.filter(user=user).select_related("show"):
            if entry.status == "REJECTED":
                continue
            if (entry.rating is not None and entry.rating >= min_rating) or entry.is_favorite:
                show = entry.show
                out.append(
                    (
                        "show",
                        show.tmdb_id,
                        f"{show.name} ({show.release_year})",
                        entry.rating,
                        show.created_by or "",
                    )
                )
        out.sort(key=lambda l: l[3] or 0, reverse=True)
        return out

    # --- harvest (TMDB list calls only; zero imports yet) ------------------

    def _harvest(self, liked, opts, stats, sleep):
        """Per-seed candidate lists from recommendations + similar pages.

        Candidates are pre-filtered against the catalog here so lower pages
        only fetch when a source is still short of SOURCE_CANDIDATE_CAP
        usable items — most loved titles' first page is already half-owned.
        """
        sources = []
        for kind, tmdb_id, label, _rating, _names in liked:
            existing = self.movie_ids if kind == "movie" else self.show_ids
            items, seen = [], set()
            for fetch, pages in (
                (services.recommendations, opts["pages"]),
                (services.similar, opts["similar_pages"]),
            ):
                for page in range(1, max(0, pages) + 1):
                    if page > 1:
                        self._pause(sleep)
                    try:
                        fetched = fetch(TMDB_MEDIA[kind], tmdb_id, page=page)
                        stats["pages"] += 1
                    except services.TMDBError as exc:
                        self.stderr.write(f"{label} {kind} page {page} failed: {exc}")
                        break
                    for item in fetched:
                        iid = item.get("id")
                        if not iid or iid == tmdb_id or iid in seen or (kind, iid) in self.attempted:
                            continue
                        seen.add(iid)
                        if iid in existing:
                            stats["existing"] += 1
                            continue
                        if (item.get("vote_count") or 0) < self.floors[kind]:
                            continue
                        self.attempted.add((kind, iid))
                        items.append(item)
                    if len(items) >= SOURCE_CANDIDATE_CAP:
                        break
                if len(items) >= SOURCE_CANDIDATE_CAP:
                    break
            sources.append((kind, label, items))
        return sources

    def _creator_sources(self, liked, opts, stats, sleep):
        """Per-person candidate lists (highest-voted first) for --creators."""
        sources, person_ids = [], {}

        def person_id_for(name):
            if name in person_ids:
                return person_ids[name]
            self._pause(sleep)
            try:
                results = services.search_person(name)
            except services.TMDBError as exc:
                self.stderr.write(f"person search '{name}' failed: {exc}")
                results = []
            person_ids[name] = results[0]["id"] if results else None
            return person_ids[name]

        for kind, tmdb_id, label, _rating, names in liked:
            merged = {}
            for name in [n.strip() for n in names.split(",") if n.strip()]:
                pid = person_id_for(name)
                if not pid:
                    continue
                self._pause(sleep)
                try:
                    payload = services.person_media_credits(pid, TMDB_MEDIA[kind])
                    stats["person_credits"] += 1
                except services.TMDBError as exc:
                    self.stderr.write(f"credits for {name} failed: {exc}")
                    continue
                for c in (payload.get("cast") or []) + (payload.get("crew") or []):
                    if c.get("id") and c["id"] != tmdb_id:
                        merged.setdefault(c["id"], c)
            items = sorted(merged.values(), key=lambda c: c.get("vote_count") or 0, reverse=True)
            if items:
                sources.append((kind, label, items))
        return sources

    # --- importing ---------------------------------------------------------

    def _import_round_robin(self, sources, remaining, opts, stats):
        """Turn-taking import: loved titles share the import budget by turn,
        so the first favorite doesn't swallow every slot. Returns True when
        the budget was the thing that stopped the loop."""
        pointers = [0] * len(sources)
        while remaining["n"] > 0 and any(
            p < len(items) for p, (_k, _l, items) in zip(pointers, sources)
        ):
            progress = False
            for si, (kind, label, items) in enumerate(sources):
                while pointers[si] < len(items):
                    if remaining["n"] <= 0:
                        return True
                    item = items[pointers[si]]
                    pointers[si] += 1
                    progress = True
                    self._import_candidate(kind, item, remaining, opts, stats)
                    if remaining["n"] <= 0:
                        return True
                if not progress and remaining["n"] <= 0:
                    return True
            if not progress:
                break
        return remaining["n"] <= 0

    def _import_creators(self, liked, opts, stats, sleep, remaining):
        for kind, person, items in self._creator_sources(liked, opts, stats, sleep):
            cap = 0
            for item in items:
                if remaining["n"] <= 0 or cap >= opts["creator_captures"]:
                    break
                if self._import_candidate(kind, item, remaining, opts, stats):
                    cap += 1
            self._pause(sleep)
        return remaining["n"] <= 0

    def _import_candidate(self, kind, item, remaining, opts, stats):
        """One candidate → catalog candidate; True when it actually imported.

        Existing tmdb_ids short-circuit locally (no TMDB call, no budget);
        imports consume budget even on TMDB errors so a flaky endpoint can't
        spin the crawl forever.
        """
        tmdb_id = item["id"]
        if (kind, tmdb_id) in self.attempted:
            return False
        self.attempted.add((kind, tmdb_id))
        existing = self.movie_ids if kind == "movie" else self.show_ids
        if tmdb_id in existing:
            stats["existing"] += 1
            return False
        stats["candidates"] += 1
        floor = opts["min_votes_movie"] if kind == "movie" else opts["min_votes_show"]
        if (item.get("vote_count") or 0) < floor:
            stats["below_floor"] += 1
            return False
        name = item.get("title") or item.get("name") or f"tmdb:{tmdb_id}"
        remaining["n"] -= 1
        try:
            _obj, imported_now = import_title(kind, tmdb_id)
        except services.TMDBError as exc:
            stats["errors"] += 1
            self.stderr.write(f"{kind}/{tmdb_id} import failed: {exc}")
            return False
        if not imported_now:
            stats["existing"] += 1
            return False
        existing.add(tmdb_id)
        stats["imported"] += 1
        if stats["imported"] % 25 == 0:
            self.stdout.write(f"  imported {stats['imported']} so far...")
        self.stdout.write(f"  + {name}")
        return True

    # --- plumbing ----------------------------------------------------------

    def _remaining(self, max_imports):
        return {"n": max_imports if max_imports > 0 else 10**9}

    def _report(self, stats, liked, sources, remaining):
        self.stdout.write(
            f"liked={len(liked)} sources={len(sources)} "
            f"recommendation-pages={stats['pages']} "
            f"person-credits={stats['person_credits']} "
            f"candidates={stats['candidates']} "
            f"imported={stats['imported']} "
            f"existing={stats['existing']} "
            f"below-floor={stats['below_floor']} "
            f"errors={stats['errors']} "
            f"budget-left={remaining['n'] if remaining['n'] < 10**9 else 'uncapped'}"
        )

    def _pause(self, seconds):
        if seconds > 0:
            time.sleep(seconds)
