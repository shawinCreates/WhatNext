"""Heuristic + semantic recommendations (Phase 4): taste vectors x genre overlap + embeddings.

Scores local catalog titles the user has no
library entry for, re-ranks with MMR, and explains from stored prefs.
Mirrors 05-recommendation-engine §§3-9 with honest stand-ins:

- semantic_similarity -> max genre-Jaccard vs liked titles + embedding cosine when available
- entity_affinity -> director/cast/writers overlap with loved titles' credits
- novelty -> constant until popularity signals are calibrated
- predicted_rating -> predict_rating (item kNN over own ratings), eval-only
  until it replaces the quality stand-in in scoring (C1)

Candidate pool: title quality (crowd votes) ordering dominates, with a fixed
random long-tail share per request — as the catalog deepens (crawl_taste,
expand_catalog), pure vote ordering would bury every modest-vote title deeper
than the pool cap and the engine would never see them.
"""

import math
import random
from datetime import timedelta

from django.db import models
from django.utils import timezone

from catalog.models import Movie, Show
from library.models import UserMovie, UserShow

from .models import MovieFeature, RecoServe, UserPreference
from .taxonomy import FEATURES

ALGORITHM_VERSION = "hybrid-embeddings-v2"
FEATURE_VERSION = "genre-heuristic-v1+embeddings"
MMR_LAMBDA = 0.5
LIKED_RATING = 8.0
MAX_CANDIDATES = 3000
LONGTAIL_SHARE = 0.25  # per-request random slice; deep-pool titles must get scored
MID_RATING = 5.5
JITTER = 0.05  # score noise shelf; near-ties reshuffle on every request
ROTATION_DAYS = 3
ROTATION_CAP = 30
SIMILAR_COSINE = 0.7  # local "more like this": cosine 0.7 + genre-Jaccard 0.3


def _cosine_np(a, b):
    try:
        import numpy as _np

        if a is None or b is None:
            return 0.0
        a = _np.array(a, dtype=_np.float32)
        b = _np.array(b, dtype=_np.float32)
        na = _np.linalg.norm(a)
        nb = _np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(_np.dot(a, b) / (na * nb))
    except Exception:
        return 0.0


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


def _entities_of(title, is_movie):
    """Director/cast/writers (movies) or creator/cast (shows)."""
    entities = set()
    if is_movie:
        director = getattr(title, "director", "") or ""
        if director:
            entities.add(director)
        cast = getattr(title, "cast", None) or []
        if isinstance(cast, list):
            for c in cast:
                if isinstance(c, str) and c:
                    entities.add(c)
        writers = getattr(title, "writers", None) or []
        if isinstance(writers, list):
            for w in writers:
                if isinstance(w, str) and w:
                    entities.add(w)
        return entities
    names = getattr(title, "created_by", "") or ""
    if names:
        for n in names.split(","):
            n = n.strip()
            if n:
                entities.add(n)
    cast = getattr(title, "cast", None) or []
    if isinstance(cast, list):
        for c in cast:
            if isinstance(c, str) and c:
                entities.add(c)
    return entities


def _entity_score(candidates_entities, liked_entities):
    """Share of the candidate's creators the user already rated ≥ 8."""
    if not candidates_entities or not liked_entities:
        return 0.0
    return len(candidates_entities & liked_entities) / len(candidates_entities)


def _liked_title_embeds(liked):
    """Average embedding of liked titles for semantic affinity."""
    embeds = []
    for l in liked:
        title_obj = l.get("_obj")
        if title_obj and getattr(title_obj, "embedding", None):
            try:
                embeds.append(title_obj.embedding)
            except Exception:
                pass
    if not embeds:
        return None
    try:
        import numpy as _np

        arr = _np.array([_np.array(e, dtype=_np.float32) for e in embeds])
        mean = arr.mean(axis=0)
        norm = _np.linalg.norm(mean)
        if norm > 0:
            mean = mean / norm
        return mean.tolist()
    except Exception:
        return None


def _semantic_embed_sim(title, liked_embeds):
    if liked_embeds is None or not getattr(title, "embedding", None):
        return 0.0
    return _cosine_np(title.embedding, liked_embeds)


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
                "entities": _entities_of(title, isinstance(entry, UserMovie)),
                "tkey": (
                    f"m{title.id}"
                    if isinstance(entry, UserMovie)
                    else f"s{title.id}"
                ),
                "_obj": title,
            }
        )
    return liked


def _vector_pool(qs, cap, target_embed):
    """SQL-side pgvector pre-filter: candidates nearest the loved-titles mean.

    Returns None whenever pgvector isn't active (jsonb columns, lib missing)
    or the query fails — the jsonb world must keep working untouched.
    """
    try:
        from catalog.models import HAS_PGVECTOR

        if not HAS_PGVECTOR:
            return None
        from pgvector.django import CosineDistance

        return list(
            qs.filter(embedding__isnull=False)
            .annotate(_dist=CosineDistance("embedding", target_embed))
            .order_by("_dist", models.F("vote_count").desc(nulls_last=True))[:cap]
        )
    except Exception:
        return None


def _pool_slice(qs, cap, target_embed=None):
    """Ordering strategy for the scoring pool.

    1. pgvector taste-order (SQL cosine to the liked-titles mean) when the
       stack is enabled: the deep pool with embeddings leads, crowd-quality
       titles backfill the slice (new imports before embed_catalog runs).
    2. Fallback (no target / no pgvector): crowd-quality ordering dominated,
       with a fixed random long-tail share — pure vote ordering would bury
       every modest-vote import beyond the pool cap.
    """
    if target_embed is not None:
        pool = _vector_pool(qs, cap, target_embed)
        if pool is not None:
            picked = {t.pk for t in pool}
            room = cap - len(pool)
            if room > 0:
                pool += list(
                    qs.exclude(pk__in=picked)
                    .order_by(
                        models.F("vote_count").desc(nulls_last=True),
                        models.F("vote_average").desc(nulls_last=True),
                    )[:room]
                )
            return pool
    quality_cap = max(1, cap - int(cap * LONGTAIL_SHARE))
    quality = list(
        qs.order_by(
            models.F("vote_count").desc(nulls_last=True),
            models.F("vote_average").desc(nulls_last=True),
        )[:quality_cap]
    )
    quality_ids = [t.pk for t in quality]
    tail = list(qs.exclude(pk__in=quality_ids).order_by("?")[: cap - len(quality)])
    return quality + tail


def _candidates(user, kind, features, skip=(), liked_embeds=None):
    lib_movie_ids = set(
        UserMovie.objects.filter(user=user).values_list("movie_id", flat=True)
    )
    lib_show_ids = set(
        UserShow.objects.filter(user=user).values_list("show_id", flat=True)
    )
    items = []
    if kind in ("all", "movie"):
        for m in _pool_slice(
            Movie.objects.exclude(id__in=lib_movie_ids).prefetch_related("genres"),
            MAX_CANDIDATES,
            liked_embeds,
        ):
            if f"m{m.id}" in skip:
                continue
            vec = features.get(f"m{m.id}")
            if vec:
                items.append(("movie", m, vec))
    if kind in ("all", "show"):
        for s in _pool_slice(
            Show.objects.exclude(id__in=lib_show_ids).prefetch_related("genres"),
            MAX_CANDIDATES,
            liked_embeds,
        ):
            if f"s{s.id}" in skip:
                continue
            vec = features.get(f"s{s.id}")
            if vec:
                items.append(("show", s, vec))
    return items


def _score_user(user, kind, features, prefs, liked_genres, liked_entities, skip, jitter, liked_embeds=None, context=None):
    """Jittered final scores for every candidate: [(score, kind, title, vec)]."""
    scored = []
    rated = _own_ratings(user)
    for k, title, vec in _candidates(
        user, kind, features, skip=skip, liked_embeds=liked_embeds
    ):
        genres = set(g.id for g in title.genres.all())
        taste_raw, semantic_genre = _score(prefs, vec, genres, liked_genres)
        # Blend embedding similarity if available (prefer embeddings)
        embed_sim = _semantic_embed_sim(title, liked_embeds)
        if embed_sim > 0 and semantic_genre >= 0:
            semantic = 0.7 * embed_sim + 0.3 * semantic_genre
        elif embed_sim > 0:
            semantic = embed_sim
        else:
            semantic = semantic_genre
        tkey = f"m{title.id}" if k == "movie" else f"s{title.id}"
        predicted, _, covered = (
            predict_rating(user, tkey, features, rated=rated) if rated else (None, None, False)
        )
        entity = _entity_score(
            _entities_of(title, k == "movie"), liked_entities
        )
        quality = _quality(title.vote_average, predicted, bool(rated))
        scored.append(
            (
                k,
                title,
                vec,
                taste_raw,
                semantic,
                quality,
                entity,
                predicted,
                covered,
            )
        )
    if not scored:
        return []
    # Min-max normalize taste to 0..1 so weights stay comparable.
    raws = [s[3] for s in scored]
    lo, hi = min(raws), max(raws)
    span = hi - lo or 1.0
    ranked = []
    for k, title, vec, raw, semantic, quality, entity, predicted, covered in scored:
        taste_n = (raw - lo) / span
        if covered and predicted is not None:
            # Renormalize: redistribute if predicted not covered (covered means True here)
            score = (
                0.40 * taste_n
                + 0.20 * semantic
                + 0.15 * quality
                + 0.15 * max(0.0, min(1.0, (predicted - 1) / 9))
                + 0.10 * entity
            )
        else:
            # Redistribute 0.15 to remaining components proportionally (sum 0.85 -> scale to 1)
            score = (0.40 * taste_n + 0.20 * semantic + 0.15 * quality + 0.10 * entity) / 0.85
        if context:
            score = _apply_context_boost(score, title, k, context)
        if jitter:
            score += random.uniform(-JITTER, JITTER)
        ranked.append((score, k, title, vec))
    return ranked


def _mmr_select(pool, count):
    """MMR diversity: relevance - lambda * max similarity to selected."""
    if not pool or count <= 0:
        return []
    selected, remaining = [pool[0]], pool[1:]
    while remaining and len(selected) < count:
        best, best_val = None, float("-inf")
        selected_vecs = [s[3] for s in selected]
        for cand in remaining:
            penalty = max((_cosine(cand[3], v) for v in selected_vecs), default=0.0)
            val = cand[0] - MMR_LAMBDA * penalty
            if val > best_val:
                best, best_val = cand, val
        selected.append(best)
        remaining.remove(best)
    return selected


def _apply_context_boost(score, title, kind, context):
    if not context:
        return score
    ctx = str(context).lower()
    boost = 1.0
    runtime = getattr(title, "runtime", None)
    if ctx == "tonight":
        if runtime and runtime <= 120:
            boost *= 1.08
        # heuristic: prefer higher vote average / shorter generally
        boost *= 1.0
    elif ctx == "weekend":
        if runtime and runtime >= 90:  # allow longer
            boost *= 1.05
    return score * boost


def _score(prefs, vec, genres, liked_genres):
    taste_raw = sum(prefs.get(k, 0.0) * v for k, v in vec.items())
    semantic = max((_jaccard(genres, lg) for lg in liked_genres), default=0.0)
    return taste_raw, semantic


def _quality(vote_average, predicted, has_ratings):
    """Crowd vote blended with the user's own kNN prediction (Phase 4 C1)."""
    vote = (vote_average / 10.0) if vote_average else None
    if not has_ratings:
        return vote if vote is not None else 0.5
    pred = max(0.0, min(1.0, (predicted - 1) / 9))
    if vote is None:
        return pred
    return 0.5 * vote + 0.5 * pred


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
        "vote_count": title.vote_count,
        "award_label": title.award_label or None,
        "created_by": getattr(title, "created_by", "") or None,
        "runtime": getattr(title, "runtime", None),
        "seasons": getattr(title, "seasons", None),
        "episodes": getattr(title, "episodes", None),
        "is_anime": getattr(title, "is_anime", None),
        "original_language": title.original_language or None,
        "genres": [{"id": g.id, "name": g.name} for g in title.genres.all()],
        "score": round(score, 4),
        "rank": rank,
        "personalized": personalized,
        "reasons": reasons,
        "similar_liked": similar,
    }


def _recent_serves(user):
    """tkeys shown to the user lately — rotated out so picks stay fresh."""
    since = timezone.now() - timedelta(days=ROTATION_DAYS)
    serves = (
        RecoServe.objects.filter(user=user, served_at__gte=since)
        .order_by("-served_at")
        .values_list("tkey", flat=True)[:ROTATION_CAP]
    )
    return set(serves)


def recommend_for_user(user, kind="all", limit=20, jitter=True, skip_recent=True, context=None):
    """Score unseen catalog titles, MMR re-rank, explain from stored prefs.

    kind="all" reserves ~a quarter of the slots for shows (min 2) so series
    always get shelf time between the point-hungry movies.
    """
    kind = kind if kind in ("movie", "show") else "all"
    limit = max(1, min(int(limit or 20), 50))
    prefs = _signed_prefs(user)
    features = _feature_map()
    liked = _liked_titles(user)
    liked_genres = [l["genres"] for l in liked if l["genres"]]
    liked_entities = set().union(*[l["entities"] for l in liked]) if liked else set()
    liked_embeds = _liked_title_embeds(liked)
    skip = _recent_serves(user) if skip_recent else set()

    ranked = _score_user(
        user, kind, features, prefs, liked_genres, liked_entities, skip, jitter, liked_embeds=liked_embeds, context=context
    )
    if len(ranked) < limit and skip:
        # Small catalog: rotated-out titles are needed to fill the page.
        ranked = _score_user(
            user, kind, features, prefs, liked_genres, liked_entities, set(), jitter, liked_embeds=liked_embeds, context=context
        )
    if not ranked:
        return []

    if kind == "all":
        shows = [r for r in ranked if r[1] == "show"]
        movies = [r for r in ranked if r[1] == "movie"]
        if shows:
            quota = min(limit - 1, len(shows), max(2, math.ceil(limit / 4)))
            picked = _mmr_select(shows, quota) + _mmr_select(movies, limit - quota)
        else:
            picked = _mmr_select(ranked, limit)
    else:
        picked = _mmr_select(ranked, limit)
    picked.sort(key=lambda r: r[0], reverse=True)

    personalized = bool(prefs)
    out = []
    for rank, (score, k, title, vec) in enumerate(picked[:limit], start=1):
        reasons, similar = _explain(prefs, vec, liked, features)
        out.append(
            _payload(k, title, score, rank, personalized and bool(reasons), reasons, similar)
        )
    return out


def log_serves(user, results):
    """Record what was actually shown so the next request rotates past it."""
    from .models import RecoImpression

    RecoServe.objects.bulk_create(
        RecoServe(
            user=user,
            tkey=f"m{r['id']}" if r["kind"] == "movie" else f"s{r['id']}",
            algorithm_version=ALGORITHM_VERSION,
            feature_version=FEATURE_VERSION,
        )
        for r in results
    )
    # Also log impressions for learning loop
    try:
        RecoImpression.objects.bulk_create(
            RecoImpression(
                user=user,
                tkey=f"m{r['id']}" if r["kind"] == "movie" else f"s{r['id']}",
                kind=r["kind"],
                title_id=r["id"],
                position=r.get("rank"),
                algorithm_version=ALGORITHM_VERSION,
                feature_version=FEATURE_VERSION,
            )
            for r in results
        )
    except Exception:
        pass
    RecoServe.objects.filter(
        user=user, served_at__lt=timezone.now() - timedelta(days=90)
    ).delete()
    try:
        RecoImpression.objects.filter(
            user=user, impression_at__lt=timezone.now() - timedelta(days=90)
        ).delete()
    except Exception:
        pass


def feedback_payload(user):
    """Funnel over served picks: later library actions (docs §6, Phase 5).

    Served titles are never in the library, so any entry for one was
    created after the serve — counts split by final status.
    """
    served = {
        s.tkey for s in RecoServe.objects.filter(user=user)
    }
    if not served:
        return {
            "served": 0,
            "watched": 0,
            "rejected": 0,
            "conversion": None,
        }
    movie_ids = {int(t[1:]) for t in served if t.startswith("m")}
    show_ids = {int(t[1:]) for t in served if t.startswith("s")}
    watched = rejected = 0
    if movie_ids:
        watched += UserMovie.objects.filter(
            user=user, movie_id__in=movie_ids, status__in=("WATCHED", "SKIPPED")
        ).count()
        rejected += UserMovie.objects.filter(
            user=user, movie_id__in=movie_ids, status="REJECTED"
        ).count()
    if show_ids:
        watched += UserShow.objects.filter(
            user=user, show_id__in=show_ids, status__in=("WATCHED", "SKIPPED")
        ).count()
        rejected += UserShow.objects.filter(
            user=user, show_id__in=show_ids, status="REJECTED"
        ).count()
    # Punted: 'clicked' tracking (docs §6) — no separate click event exists.
    return {
        "served": len(served),
        "watched": watched,
        "rejected": rejected,
        "conversion": round(watched / len(served), 4),
    }


def similar_for_title(user, kind, title, limit=12):
    """Local content-based 'more like this': feature-vector cosine plus genre
    overlap scored against every same-kind catalog title not already shelved."""
    lib_ids = set(
        UserMovie.objects.filter(user=user).values_list("movie_id", flat=True)
        if kind == "movie"
        else UserShow.objects.filter(user=user).values_list("show_id", flat=True)
    )
    features = _feature_map()
    target = features.get(f"m{title.id}" if kind == "movie" else f"s{title.id}") or {}
    target_genres = set(g.id for g in title.genres.all())

    model = Movie if kind == "movie" else Show
    scored = []
    for other in model.objects.exclude(id__in=lib_ids).prefetch_related("genres"):
        if other.id == title.id or not other.poster_path:
            continue
        vec = features.get(f"m{other.id}" if kind == "movie" else f"s{other.id}") or {}
        genres = set(g.id for g in other.genres.all())
        sim_feat = _cosine(target, vec)
        sim_gen = _jaccard(genres, target_genres)
        sim_emb = _cosine_np(getattr(title, "embedding", None), getattr(other, "embedding", None))
        if sim_emb > 0:
            similarity = 0.7 * sim_emb + 0.2 * sim_feat + 0.1 * sim_gen
        else:
            similarity = (
                SIMILAR_COSINE * sim_feat
                + (1 - SIMILAR_COSINE) * sim_gen
            )
        scored.append((similarity, other))
    scored.sort(key=lambda s: s[0], reverse=True)

    return [
        {
            "local": True,
            "kind": kind,
            "id": other.id,
            "tmdb_id": other.tmdb_id,
            "title": getattr(other, "title", None) or other.name,
            "year": other.release_year,
            "poster_path": other.poster_path,
        }
        for _, other in scored[:limit]
    ]


def run_meta():
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "feature_version": FEATURE_VERSION,
        "generated_at": timezone.now().isoformat(),
    }


def _own_ratings(user):
    """tkey -> own rating for the user's rated titles."""
    rated = {}
    for mid, r in UserMovie.objects.filter(
        user=user, rating__isnull=False
    ).values_list("movie_id", "rating"):
        rated[f"m{mid}"] = r
    for sid, r in UserShow.objects.filter(
        user=user, rating__isnull=False
    ).values_list("show_id", "rating"):
        rated[f"s{sid}"] = r
    return rated


def predict_rating(user, tkey, features, rated=None, k=10):
    """Predicted rating for a title: cosine-weighted mean of own ratings.

    Neighbors are the k most similar rated titles in feature space
    (item kNN, 06 §§2/8). Falls back to the user's mean rating when no
    rated title shares a feature. Returns (prediction, mean_baseline,
    covered) so eval can compare like for like (A1). Pass `rated` (see
    _own_ratings) to reuse one dict across many calls.
    """
    rated = _own_ratings(user) if rated is None else dict(rated)
    rated.pop(tkey, None)  # the target's own rating must not predict itself
    if not rated:
        return MID_RATING, MID_RATING, False
    base = sum(rated.values()) / len(rated)
    target = features.get(tkey) or {}
    sims = sorted(
        (
            (sim, rating)
            for rkey, rating in rated.items()
            if (sim := _cosine(target, features.get(rkey, {}))) > 0
        ),
        key=lambda s: s[0],
        reverse=True,
    )[:k]
    if not sims:
        return base, base, False
    total = sum(sim for sim, _ in sims)
    return sum(sim * r for sim, r in sims) / total, base, True
