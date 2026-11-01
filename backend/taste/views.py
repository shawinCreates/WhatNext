from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from library.views import current_user

from .reco import (
    feedback_payload,
    log_serves,
    recommend_for_user,
    run_meta,
    similar_for_title,
)
from .services import backfill_features, build_profile, profile_payload


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
    try:
        limit = int(request.query_params.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    results = recommend_for_user(user, kind=kind, limit=limit)
    log_serves(user, results)
    payload = {"results": results}
    payload.update(run_meta())
    return Response(payload)


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
