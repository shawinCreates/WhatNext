"""Catalog pool health: sizes, library overlap, coverage, decades, genres.

The recommendation pool is catalog minus library (any status). Beyond raw
counts this reports feature/backfill coverage (titles without features are
invisible to scoring) and embedding coverage (titles without embeddings fall
back to genre-only semantic signal). Run after crawl_taste / expand_catalog
to see the pool deepen, before embed_catalog to see what still needs vectors.
"""

import json

from django.core.management.base import BaseCommand
from django.db.models import Count

from catalog.models import Genre, Movie, Show
from library.models import UserMovie, UserShow


def _bucket(year):
    return f"{(year // 10) * 10}s" if year else None


def pool_report():
    movie_ids = set(Movie.objects.values_list("id", flat=True))
    show_ids = set(Show.objects.values_list("id", flat=True))
    lib_movie_ids = set(UserMovie.objects.values_list("movie_id", flat=True))
    lib_show_ids = set(UserShow.objects.values_list("show_id", flat=True))

    from taste.models import MovieFeature  # lazy: taste depends on catalog

    featured_movies = set(
        MovieFeature.objects.exclude(movie=None).values_list("movie_id", flat=True)
    )
    featured_shows = set(
        MovieFeature.objects.exclude(show=None).values_list("show_id", flat=True)
    )
    embedded_movies = set(
        Movie.objects.filter(embedding__isnull=False).values_list("id", flat=True)
    )
    embedded_shows = set(
        Show.objects.filter(embedding__isnull=False).values_list("id", flat=True)
    )

    decades = {}
    for model in (Movie, Show):
        for year in model.objects.exclude(release_year=None).values_list(
            "release_year", flat=True
        ).iterator():
            key = _bucket(year)
            decades[key] = decades.get(key, 0) + 1

    genre_rows = Genre.objects.annotate(
        m=Count("movies", distinct=True), s=Count("shows", distinct=True)
    ).values("name", "m", "s")
    genres_top = sorted(genre_rows, key=lambda g: g["m"] + g["s"], reverse=True)[:10]

    return {
        "catalog": {
            "movies": len(movie_ids),
            "shows": len(show_ids),
            "total": len(movie_ids) + len(show_ids),
        },
        "library": {
            "movie_entries": len(lib_movie_ids),
            "show_entries": len(lib_show_ids),
        },
        "recommendation_pool": {
            "movie_candidates": len(movie_ids - lib_movie_ids),
            "show_candidates": len(show_ids - lib_show_ids),
        },
        "coverage": {
            "movie_features": len(featured_movies & movie_ids),
            "movie_features_missing": len(movie_ids - featured_movies),
            "show_features": len(featured_shows & show_ids),
            "show_features_missing": len(show_ids - featured_shows),
            "movie_embeddings": len(embedded_movies),
            "movie_embeddings_missing": len(movie_ids - embedded_movies),
            "show_embeddings": len(embedded_shows),
            "show_embeddings_missing": len(show_ids - embedded_shows),
        },
        "decades": dict(sorted(decades.items(), key=lambda kv: (kv[0] or ""))),
        "genres_top": [
            {"name": g["name"], "movies": g["m"], "shows": g["s"]} for g in genres_top
        ],
    }


class Command(BaseCommand):
    help = "Catalog pool health: sizes, library overlap, feature/embedding coverage."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="machine-readable output")

    def handle(self, *args, **opts):
        report = pool_report()
        if opts["json"]:
            self.stdout.write(json.dumps(report, indent=2))
            return
        self.stdout.write(
            f"catalog    {report['catalog']['movies']} movies, "
            f"{report['catalog']['shows']} shows "
            f"(total {report['catalog']['total']})"
        )
        self.stdout.write(
            f"library    {report['library']['movie_entries']} movie entries, "
            f"{report['library']['show_entries']} show entries"
        )
        self.stdout.write(
            f"reco pool  {report['recommendation_pool']['movie_candidates']} movie "
            f"candidates, {report['recommendation_pool']['show_candidates']} show "
            f"candidates"
        )
        cov = report["coverage"]
        self.stdout.write(
            f"features   movies {cov['movie_features']}/{report['catalog']['movies']} "
            f"(missing {cov['movie_features_missing']}), "
            f"shows {cov['show_features']}/{report['catalog']['shows']} "
            f"(missing {cov['show_features_missing']})"
        )
        self.stdout.write(
            f"embeddings movies {cov['movie_embeddings']}/{report['catalog']['movies']} "
            f"(missing {cov['movie_embeddings_missing']}), "
            f"shows {cov['show_embeddings']}/{report['catalog']['shows']} "
            f"(missing {cov['show_embeddings_missing']})"
        )
        if report["decades"]:
            self.stdout.write(
                "decades    "
                + "  ".join(f"{d}: {n}" for d, n in report["decades"].items())
            )
        if report["genres_top"]:
            self.stdout.write(
                "genres     "
                + "  ".join(
                    f"{g['name']}: {g['movies']}m/{g['shows']}s"
                    for g in report["genres_top"]
                )
            )
