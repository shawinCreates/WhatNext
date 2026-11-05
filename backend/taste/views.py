from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from library.views import current_user

from catalog.models import Movie, Show
from library.models import UserMovie, UserShow

from .reco import (
    feedback_payload,
    log_serves,
    recommend_for_user,
    run_meta,
    similar_for_title,
)
from .services import backfill_features, build_profile, profile_payload
from .models import PairwiseComparison


@api_view(["GET"])
def taste_profile(request):
    return Response(profile_payload(current_user(request)))


@api_view(["GET"])
def recommendations_feedback(request):
    return Response(feedback_payload(current_user(request)))


@api_view(["GET"])
def recommendations(request):
    user = current_user(request)
    kind = request.query_params.get("kind", "all")
    context = request.query_params.get("context")
    try:
        limit = int(request.query_params.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    results = recommend_for_user(user, kind=kind, limit=limit, context=context)
    log_serves(user, results)
    payload = {"results": results}
    payload.update(run_meta())
    return Response(payload)


@api_view(["POST"])
def recommendation_click(request):
    user = current_user(request)
    tkey = request.data.get("tkey") or request.data.get("key")
    title_id = request.data.get("id") or request.data.get("title_id")
    kind = request.data.get("kind")
    from django.utils import timezone

    from .models import RecoImpression

    if tkey:
        try:
            imp = RecoImpression.objects.filter(user=user, tkey=tkey).order_by("-impression_at").first()
            if imp and not imp.clicked:
                imp.clicked = True
                imp.clicked_at = timezone.now()
                imp.save(update_fields=["clicked", "clicked_at"])
        except Exception:
            pass
    try:
        RecoImpression.objects.create(
            user=user,
            tkey=tkey or f"{kind[0]}{title_id}" if kind and title_id else (tkey or ""),
            kind=kind or "",
            title_id=title_id,
            clicked=True,
            clicked_at=timezone.now(),
        )
    except Exception:
        pass
    return Response({"ok": True})


@api_view(["GET"])
def similar_titles(request, kind, pk):
    """'More like this': local content-based matches, TMDB tops it up."""
    user = current_user(request)
    if kind not in ("movie", "show"):
        return Response(
            {"detail": "kind must be 'movie' or 'show'"}, status=status.HTTP_400_BAD_REQUEST
        )
    from catalog.models import Movie, Show
    from catalog.services import TMDBError, similar as tmdb_similar

    title_model, media = (Movie, "movie") if kind == "movie" else (Show, "tv")
    try:
        title = title_model.objects.prefetch_related("genres").get(pk=pk)
    except title_model.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    try:
        limit = int(request.query_params.get("limit", 12))
    except (TypeError, ValueError):
        limit = 12
    limit = max(1, min(limit, 50))

    results = similar_for_title(user, kind, title, limit=limit)
    if len(results) < limit:
        seen = {r["tmdb_id"] for r in results}
        try:
            extras = tmdb_similar(media, title.tmdb_id)
        except TMDBError:
            extras = []
        for extra in extras:
            extra_id = extra.get("id")
            if not extra_id or extra_id in seen:
                continue
            seen.add(extra_id)
            local_date = extra.get("release_date") or extra.get("first_air_date") or ""
            results.append(
                {
                    "local": False,
                    "kind": kind,
                    "id": extra_id,
                    "tmdb_id": extra_id,
                    "title": extra.get("title") or extra.get("name") or "Untitled",
                    "year": int(local_date[:4] or 0) or None,
                    "poster_path": extra.get("poster_path") or None,
                }
            )
            if len(results) >= limit:
                break
    return Response({"results": results})


@api_view(["POST"])
def recommendations_refresh(request):
    user = current_user(request)
    backfill_features()
    count = build_profile(user)
    payload = {"rebuilt_preferences": count}
    payload.update(run_meta())
    return Response(payload)


def _pair_title_payload(kind, title):
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
        "overview": title.overview,
        "vote_average": title.vote_average,
        "genres": [{"id": g.id, "name": g.name} for g in title.genres.all()],
        "tkey": f"m{title.id}" if kind == "movie" else f"s{title.id}",
    }


def _pick_pair(user):
    """Two unseen catalog titles to compare, preferring a shared genre."""
    lib_movie_ids = set(
        UserMovie.objects.filter(user=user).values_list("movie_id", flat=True)
    )
    lib_show_ids = set(
        UserShow.objects.filter(user=user).values_list("show_id", flat=True)
    )
    pool = [
        ("movie", m)
        for m in Movie.objects.exclude(id__in=lib_movie_ids).prefetch_related("genres")
    ] + [
        ("show", s)
        for s in Show.objects.exclude(id__in=lib_show_ids).prefetch_related("genres")
    ]
    if len(pool) < 2:
        return pool
    import random

    random.shuffle(pool)
    for i, (k1, t1) in enumerate(pool):
        g1 = set(g.id for g in t1.genres.all())
        for k2, t2 in pool[i + 1 :]:
            if g1 & set(g.id for g in t2.genres.all()):
                return [(k1, t1), (k2, t2)]
    return pool[:2]


@api_view(["GET"])
def taste_pair(request):
    """One pair of unseen titles for the user to compare."""
    user = current_user(request)
    pair = _pick_pair(user)
    if len(pair) < 2:
        return Response(
            {"detail": "Not enough unseen titles to compare."},
            status=status.HTTP_404_NOT_FOUND,
        )
    (ka, ta), (kb, tb) = pair
    return Response({"a": _pair_title_payload(ka, ta), "b": _pair_title_payload(kb, tb)})


@api_view(["POST"])
def taste_pair_submit(request):
    """Record an explicit A-over-B (or tie) preference."""
    user = current_user(request)
    tkey_a = request.data.get("tkey_a")
    tkey_b = request.data.get("tkey_b")
    winner_tkey = request.data.get("winner_tkey")
    if not tkey_a or not tkey_b or not winner_tkey:
        return Response(
            {"detail": "tkey_a, tkey_b, and winner_tkey are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # Normalize storage order so the same pair can't be duplicated either way.
    if tkey_a > tkey_b:
        tkey_a, tkey_b = tkey_b, tkey_a
    if winner_tkey not in (tkey_a, tkey_b, "tie", "neither"):
        return Response(
            {"detail": "winner_tkey must be tkey_a, tkey_b, or tie"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    PairwiseComparison.objects.update_or_create(
        user=user,
        tkey_a=tkey_a,
        tkey_b=tkey_b,
        defaults={"winner_tkey": winner_tkey},
    )
    return Response({"ok": True})


@api_view(["GET"])
def taste_pairs(request):
    """The user's past pairwise comparisons (most recent first)."""
    user = current_user(request)
    rows = (
        PairwiseComparison.objects.filter(user=user)
        .order_by("-created_at")
        .values("id", "tkey_a", "tkey_b", "winner_tkey", "created_at")
    )
    return Response(
        {
            "results": [
                {
                    **r,
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in rows
            ]
        }
    )

