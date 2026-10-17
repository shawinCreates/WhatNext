"""Heuristic recommendations (Phase 4 Slice 1): taste vectors x genre overlap.

No ML, no embeddings. Scores local catalog titles the user has no
library entry for, re-ranks with MMR, and explains from stored prefs.
Mirrors 05-recommendation-engine §§3-9 with honest stand-ins:

- semantic_similarity -> max genre-Jaccard vs liked titles (no embeddings yet)
- entity_affinity -> 0 (no cast/crew stored; see catalog/models.py)
- novelty -> constant until popularity signals are calibrated
"""

import math
from django.utils import timezone

from catalog.models import Movie, Show
from library.models import UserMovie, UserShow

from .models import MovieFeature, UserPreference
from .taxonomy import FEATURES

ALGORITHM_VERSION = "heuristic-v1"
FEATURE_VERSION = "genre-heuristic-v1"
MMR_LAMBDA = 0.5
LIKED_RATING = 8.0
MAX_CANDIDATES = 1000


def _signed_prefs(user):
    prefs = {}
    for pref in UserPreference.objects.filter(user=user):
        if pref.feature_key in FEATURES:
            prefs[pref.feature_key] = pref.polarity * pref.weight
    return prefs


def _feature_map():
    """title key ('m'<id> / 's'<id>) -> {feature_key: value * confidence}."""
    out = {}
    for feat in MovieFeature.objects.all():
        key = f"m{feat.movie_id}" if feat.movie_id else f"s{feat.show_id}"
        out.setdefault(key, {})[feat.feature_key] = feat.value * feat.confidence
    return out


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / len(a | b) if inter else 0.0


def _cosine(a, b):
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in a.keys() & b.keys())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def _liked_titles(user):
    """High-rated library titles with genres + feature keys for overlap/provenance."""
    liked = []
    movies = UserMovie.objects.filter(
        user=user, rating__gte=LIKED_RATING
    ).select_related("movie")
    shows = UserShow.objects.filter(
        user=user, rating__gte=LIKED_RATING
    ).select_related("show")
    for entry in list(movies) + list(shows):
        title = entry.movie if isinstance(entry, UserMovie) else entry.show
        name = getattr(title, "title", None) or title.name
        liked.append(
            {
                "title": name,
                "year": title.release_year,
                "rating": entry.rating,
                "genres": set(g.id for g in title.genres.all()),
                "tkey": (
                    f"m{title.id}"
                    if isinstance(entry, UserMovie)
                    else f"s{title.id}"
                ),
            }
        )
    return liked


def _candidates(user, kind, features):
    lib_movie_ids = set(
        UserMovie.objects.filter(user=user).values_list("movie_id", flat=True)
    )
    lib_show_ids = set(
        UserShow.objects.filter(user=user).values_list("show_id", flat=True)
    )
    items = []
    if kind in ("all", "movie"):
        for m in (
            Movie.objects.exclude(id__in=lib_movie_ids)
            .prefetch_related("genres")
            .order_by("-vote_count", "-vote_average")[:MAX_CANDIDATES]
        ):
            vec = features.get(f"m{m.id}")
            if vec:
                items.append(("movie", m, vec))
    if kind in ("all", "show"):
        for s in (
            Show.objects.exclude(id__in=lib_show_ids)
            .prefetch_related("genres")
            .order_by("-vote_count", "-vote_average")[:MAX_CANDIDATES]
        ):
            vec = features.get(f"s{s.id}")
            if vec:
                items.append(("show", s, vec))
    return items


def _score(prefs, vec, genres, liked_genres, vote_average):
    taste_raw = sum(prefs.get(k, 0.0) * v for k, v in vec.items())
    semantic = max((_jaccard(genres, lg) for lg in liked_genres), default=0.0)
    quality = (vote_average / 10.0) if vote_average else 0.5
    return taste_raw, semantic, quality


def _explain(prefs, vec, liked, features):
    contribs = sorted(
        (
            (k, prefs[k] * vec[k])
            for k in vec.keys() & prefs.keys()
            if prefs[k] > 0 and prefs[k] * vec[k] > 0
        ),
        key=lambda kv: kv[1],
        reverse=True,
    )[:3]
    reasons = [
        {
            "feature": k,
            "label": FEATURES[k][1],
            "strength": round(c, 4),
        }
        for k, c in contribs
        if k in FEATURES
    ]
    top_keys = {k for k, _ in contribs}
    seen, similar = set(), []
    for like in sorted(liked, key=lambda l: l["rating"] or 0, reverse=True):
        like_keys = set(features.get(like["tkey"], {})) & top_keys
        if like_keys and like["title"] not in seen:
            seen.add(like["title"])
            similar.append(
                {
                    "title": like["title"],
                    "year": like["year"],
                    "rating": like["rating"],
                }
            )
        if len(similar) == 3:
            break
    return reasons, similar


def _payload(kind, title, score, rank, personalized, reasons, similar):
    name = getattr(title, "title", None) or title.name
    date = getattr(title, "release_date", None) or getattr(
        title, "first_air_date", None
    )
    return {
        "kind": kind,
        "id": title.id,
        "tmdb_id": title.tmdb_id,
        "title": name,
        "year": title.release_year,
        "release_date": date.isoformat() if date else None,
        "poster_path": title.poster_path,
        "backdrop_path": title.backdrop_path,
        "overview": title.overview,
        "vote_average": title.vote_average,
        "score": round(score, 4),
        "rank": rank,
        "personalized": personalized,
        "reasons": reasons,
        "similar_liked": similar,
    }


def recommend_for_user(user, kind="all", limit=20):
    """Score unseen catalog titles, MMR re-rank, explain from stored prefs."""
    kind = kind if kind in ("movie", "show") else "all"
    limit = max(1, min(int(limit or 20), 50))
    prefs = _signed_prefs(user)
    features = _feature_map()
    liked = _liked_titles(user)
    liked_genres = [l["genres"] for l in liked if l["genres"]]

    scored = []
    for k, title, vec in _candidates(user, kind, features):
        genres = set(g.id for g in title.genres.all())
        taste_raw, semantic, quality = _score(
            prefs, vec, genres, liked_genres, title.vote_average
        )
        scored.append((k, title, vec, taste_raw, semantic, quality))
    if not scored:
        return []

    # Min-max normalize taste to 0..1 so weights stay comparable.
    raws = [s[3] for s in scored]
    lo, hi = min(raws), max(raws)
    span = hi - lo or 1.0
    ranked = []
    for k, title, vec, raw, semantic, quality in scored:
        # shortcut: novelty fixed until popularity calibration lands (Phase 5).
        score = (
            0.50 * ((raw - lo) / span)
            + 0.25 * semantic
            + 0.15 * quality
            + 0.10 * 0.5
        )
        ranked.append((score, k, title, vec))
    ranked.sort(key=lambda r: r[0], reverse=True)

    # MMR diversity: relevance - lambda * max similarity to selected.
    selected, remaining = [ranked[0]], ranked[1:]
    while remaining and len(selected) < limit:
        best, best_val = None, float("-inf")
        selected_vecs = [s[3] for s in selected]
        for cand in remaining:
            penalty = max((_cosine(cand[3], v) for v in selected_vecs), default=0.0)
            val = cand[0] - MMR_LAMBDA * penalty
            if val > best_val:
                best, best_val = cand, val
        selected.append(best)
        remaining.remove(best)

    personalized = bool(prefs)
    out = []
    for rank, (score, k, title, vec) in enumerate(selected[:limit], start=1):
        reasons, similar = _explain(prefs, vec, liked, features)
        out.append(
            _payload(k, title, score, rank, personalized and bool(reasons), reasons, similar)
        )
    return out


def run_meta():
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "feature_version": FEATURE_VERSION,
        "generated_at": timezone.now().isoformat(),
    }
