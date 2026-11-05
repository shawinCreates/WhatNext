"""Deterministic taste profile (Phase 3 Slice 1): ratings x heuristic vectors.

No ML, no external services. LLM extraction and embeddings refine
these weights later; the loop (backfill -> build -> serve) stays the same.
"""

import math

from django.utils import timezone

from catalog.models import Movie, Show
from library.models import UserMovie, UserShow

from .models import MovieFeature, PairwiseComparison, UserPreference
from .taxonomy import FEATURES, GENRE_FEATURES, rating_weight

HEURISTIC_CONFIDENCE = 0.5
RECENCY_HALFLIFE_DAYS = 730
STRONG_EVIDENCE = 3
STRONG_WEIGHT = 0.75
REJECT_SCALE = 0.5  # unrated "Not for me" ≈ a 4-star shouting match (Phase 5)
PAIRWISE_WEIGHT = 0.3  # explicit A-over-B preference signal (V1)


def _recency(age_days):
    return math.exp(-math.log(2) * max(age_days, 0) / RECENCY_HALFLIFE_DAYS)


def _entry_multiplier(entry):
    mult = 1.2 if entry.is_favorite else 1.0
    return mult + min(entry.rewatched_count * 0.1, 0.3)


def _priors_for_genres(genres):
    priors = {}
    for genre in genres:
        for key, value in GENRE_FEATURES.get(genre.name, {}).items():
            priors[key] = max(priors.get(key, 0), value)
    return priors


def backfill_title(movie=None, show=None):
    """(Re)create heuristic MovieFeatures for one catalog title."""
    if bool(movie) == bool(show):
        raise ValueError("pass exactly one of movie, show")
    title = movie or show
    field = "movie" if movie else "show"
    priors = _priors_for_genres(title.genres.all())
    created = updated = 0
    for key, value in priors.items():
        _, was_created = MovieFeature.objects.update_or_create(
            **{field: title, "feature_key": key},
            defaults={
                "value": value,
                "confidence": HEURISTIC_CONFIDENCE,
                "source": "heuristic",
            },
        )
        created += was_created
        updated += not was_created
    return created, updated


def backfill_features():
    """(Re)create heuristic MovieFeatures for every catalog title with genres."""
    created = updated = 0
    for model, kw in ((Movie, "movie"), (Show, "show")):
        for title in model.objects.prefetch_related("genres"):
            c, u = backfill_title(**{kw: title})
            created += c
            updated += u
    return created, updated


def _contributions(user):
    """Per-feature signed contributions with provenance for one user.

    WATCHED/skipped ratings feed positive evidence; REJECTED entries feed
    negative evidence (explicit negative feedback, 06 §3 / Phase 5) —
    regardless of whether they carry a rating.
    """
    now = timezone.now()
    out = []
    for entry in UserMovie.objects.filter(user=user).select_related("movie"):
        if entry.status == "REJECTED":
            out.extend(_entry_items(entry, entry.movie, True, now, reject=True))
        elif entry.rating is not None:
            out.extend(_entry_items(entry, entry.movie, True, now))
    for entry in UserShow.objects.filter(user=user).select_related("show"):
        if entry.status == "REJECTED":
            out.extend(_entry_items(entry, entry.show, False, now, reject=True))
        elif entry.rating is not None:
            out.extend(_entry_items(entry, entry.show, False, now))
    return out


def _entry_items(entry, title, is_movie, now, reject=False):
    feats = MovieFeature.objects.filter(
        **({"movie": title} if is_movie else {"show": title})
    )
    if not feats:
        return []
    age = (now - entry.updated_at).days
    if reject:
        # Rejection counts regardless of rating; favorite/rewatch don't apply.
        scale = -REJECT_SCALE * _recency(age)
        rating = entry.rating
    else:
        scale = rating_weight(entry.rating) * _entry_multiplier(entry) * _recency(age)
        rating = entry.rating
    year = title.release_year
    name = getattr(title, "title", None) or title.name
    return [
        {
            "feature": feat.feature_key,
            "contribution": scale * feat.value * feat.confidence,
            "title": name,
            "year": year,
            "rating": rating,
        }
        for feat in feats
    ]


def _title_for_tkey(tkey):
    """Map 'm<id>' / 's<id>' back to its catalog title object, or None."""
    if not tkey or len(tkey) < 2:
        return None
    prefix, id_part = tkey[0], tkey[1:]
    try:
        pk = int(id_part)
    except (TypeError, ValueError):
        return None
    if prefix == "m":
        return Movie.objects.filter(id=pk).first()
    if prefix == "s":
        return Show.objects.filter(id=pk).first()
    return None


def _pairwise_contributions(user):
    """Signed feature contributions from explicit pairwise comparisons.

    A win lifts the winner's features and presses the loser's, so a
    consistent A-over-B preference shapes the profile without a rating.
    """
    out = []
    for comp in (
        PairwiseComparison.objects.filter(user=user)
        .exclude(winner_tkey="tie")
        .only("tkey_a", "tkey_b", "winner_tkey")
    ):
        winner_tkey = comp.winner_tkey
        if winner_tkey == "neither":
            # Neither title is liked: press both feature sets negatively.
            titles = [
                (_title_for_tkey(comp.tkey_a), comp.tkey_a),
                (_title_for_tkey(comp.tkey_b), comp.tkey_b),
            ]
            for title, _ in titles:
                if not title:
                    continue
                is_movie = isinstance(title, Movie)
                feats = MovieFeature.objects.filter(
                    **({"movie": title} if is_movie else {"show": title})
                )
                name = getattr(title, "title", None) or title.name
                year = title.release_year
                for feat in feats:
                    out.append(
                        {
                            "feature": feat.feature_key,
                            "contribution": -PAIRWISE_WEIGHT * feat.value * feat.confidence,
                            "title": name,
                            "year": year,
                            "rating": None,
                        }
                    )
            continue
        winner = _title_for_tkey(winner_tkey)
        loser_tkey = comp.tkey_b if winner_tkey == comp.tkey_a else comp.tkey_a
        loser = _title_for_tkey(loser_tkey)
        if not winner or not loser:
            continue
        winner_is_movie = isinstance(winner, Movie)
        loser_is_movie = isinstance(loser, Movie)
        winner_feats = MovieFeature.objects.filter(
            **({"movie": winner} if winner_is_movie else {"show": winner})
        )
        loser_feats = MovieFeature.objects.filter(
            **({"movie": loser} if loser_is_movie else {"show": loser})
        )
        wname = getattr(winner, "title", None) or winner.name
        lname = getattr(loser, "title", None) or loser.name
        wyear = winner.release_year
        lyear = loser.release_year
        for feat in winner_feats:
            out.append(
                {
                    "feature": feat.feature_key,
                    "contribution": PAIRWISE_WEIGHT * feat.value * feat.confidence,
                    "title": wname,
                    "year": wyear,
                    "rating": None,
                }
            )
        for feat in loser_feats:
            out.append(
                {
                    "feature": feat.feature_key,
                    "contribution": -PAIRWISE_WEIGHT * feat.value * feat.confidence,
                    "title": lname,
                    "year": lyear,
                    "rating": None,
                }
            )
    return out


def build_profile(user):
    """Rebuild all UserPreferences for one user (ratings + pairwise signals).

    Pairwise comparisons add explicit A-over-B evidence on top of rating-
    sourced preferences. Both sources are cleared and rebuilt together so a
    feature keeps a single aggregated preference.
    """
    rating_contribs = _contributions(user)
    pairwise_contribs = _pairwise_contributions(user)
    contribs = rating_contribs + pairwise_contribs
    UserPreference.objects.filter(
        user=user, source__in=("ratings", "pairwise")
    ).delete()
    totals = {}
    rating_keys = set()
    for item in rating_contribs:
        agg = totals.setdefault(
            item["feature"], {"total": 0.0, "titles": set()}
        )
        agg["total"] += item["contribution"]
        agg["titles"].add(item["title"])
        rating_keys.add(item["feature"])
    for item in pairwise_contribs:
        agg = totals.setdefault(
            item["feature"], {"total": 0.0, "titles": set()}
        )
        agg["total"] += item["contribution"]
        if item.get("title"):
            agg["titles"].add(item["title"])
    prefs = []
    for key, agg in totals.items():
        if key not in FEATURES or agg["total"] == 0:
            continue
        evidence = len(agg["titles"])
        prefs.append(
            UserPreference(
                user=user,
                feature_key=key,
                polarity=1 if agg["total"] >= 0 else -1,
                weight=round(abs(agg["total"]), 4),
                confidence=round(min(1.0, evidence / 5), 4),
                source="ratings" if key in rating_keys else "pairwise",
            )
        )
    UserPreference.objects.bulk_create(prefs)
    return len(prefs)


def _strength(evidence, weight):
    if evidence >= STRONG_EVIDENCE and weight >= STRONG_WEIGHT:
        return "strong"
    return "emerging"


def profile_payload(user):
    """Dashboard-ready profile with top supporting titles per feature."""
    if not UserPreference.objects.filter(user=user).exists():
        backfill_features()
        build_profile(user)
    contribs = _contributions(user)
    by_feature = {}
    for item in contribs:
        by_feature.setdefault(item["feature"], []).append(item)
    groups = {"positive": [], "negative": []}
    prefs = UserPreference.objects.filter(user=user).select_related("user")
    for pref in prefs:
        if pref.feature_key not in FEATURES:
            continue
        items = sorted(
            by_feature.get(pref.feature_key, []),
            key=lambda i: i["contribution"],
            reverse=pref.polarity > 0,
        )
        seen, titles = set(), []
        for item in items:
            if item["title"] not in seen:
                seen.add(item["title"])
                titles.append(
                    {
                        "title": item["title"],
                        "year": item["year"],
                        "rating": item["rating"],
                    }
                )
            if len(titles) == 3:
                break
        _, label, description = FEATURES[pref.feature_key]
        evidence = len({i["title"] for i in by_feature.get(pref.feature_key, [])})
        groups["positive" if pref.polarity > 0 else "negative"].append(
            {
                "feature": pref.feature_key,
                "label": label,
                "description": description,
                "weight": round(pref.weight if pref.polarity > 0 else -pref.weight, 4),
                "evidence": evidence,
                "strength": _strength(evidence, pref.weight),
                "titles": titles,
            }
        )
    for key in groups:
        groups[key].sort(key=lambda p: abs(p["weight"]), reverse=True)
    return {
        "positive": groups["positive"],
        "negative": groups["negative"],
        "generated_at": timezone.now().isoformat(),
    }
