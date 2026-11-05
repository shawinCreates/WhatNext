"""Shared catalog ingest: one TMDB details call per title, credits appended.

`import_title` is the canonical path for every bulk importer (refresh_catalog,
crawl_taste, expand_catalog): details + credits land in a single request, then
upsert, cast/writers (mirroring backfill_credits' mapping), and taste features.

Movies carry director/cast/writers in the appended credits block; shows get
cast there (created_by already ships with TV details). Halves the TMDB calls
per title compared to the old details-then-credits-then-director sequence.
"""

from . import services


def _director_from_credits(crew):
    """Top-billed Director from a credits crew list ('' when absent)."""
    return next(
        (c.get("name", "") for c in crew if c.get("job") == "Director"), ""
    )[:300]


def _writers_from_credits(crew):
    """Writer-ish crew names, first-billed first (same set backfill_credits uses)."""
    writers = []
    for c in crew:
        job = (c.get("job") or "").lower()
        if job in ("writer", "screenplay", "story", "teleplay", "author"):
            name = c.get("name")
            if name and name not in writers:
                writers.append(name)
    return writers


def _cast_from_credits(cast):
    """Top 10 billed names; empty list stays empty (no cast data ≠ wipe intent)."""
    return [c.get("name") for c in cast[:10] if c.get("name")]


def import_title(media, tmdb_id):
    """Import or refresh one TMDB title as a catalog candidate.

    Returns (title_obj, imported_now): existing tmdb_ids are refreshed in
    place but report imported_now=False so bulk tools skip counting them.
    Raises TMDBError when TMDB fails; the caller decides pacing and retries.
    """
    if media not in ("movie", "show"):
        raise ValueError(f"unknown media: {media}")

    from taste.services import backfill_title  # lazy: taste imports catalog.models

    model = services.Movie if media == "movie" else services.Show
    imported_now = not model.objects.filter(tmdb_id=tmdb_id).exists()

    if media == "movie":
        payload = services.get_movie(tmdb_id, append="credits")
        credits_payload = payload.get("credits") or {}
        crew = credits_payload.get("crew") or []
        movie = services.upsert_movie(
            payload, director=_director_from_credits(crew)
        )
        movie.cast = _cast_from_credits(credits_payload.get("cast") or [])
        movie.writers = _writers_from_credits(crew)
        movie.save(update_fields=["cast", "writers"])
        backfill_title(movie=movie)
        return movie, imported_now

    payload = services.get_show(tmdb_id, append="credits")
    credits_payload = payload.get("credits") or {}
    show = services.upsert_show(payload)
    show.cast = _cast_from_credits(credits_payload.get("cast") or [])
    show.save(update_fields=["cast"])
    backfill_title(show=show)
    return show, imported_now
