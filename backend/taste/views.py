from rest_framework.decorators import api_view
from rest_framework.response import Response

from library.views import current_user

from .reco import recommend_for_user, run_meta
from .services import backfill_features, build_profile, profile_payload


@api_view(["GET"])
def taste_profile(request):
    return Response(profile_payload(current_user(request)))


@api_view(["GET"])
def recommendations(request):
    user = current_user(request)
    kind = request.query_params.get("kind", "all")
    try:
        limit = int(request.query_params.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    payload = {"results": recommend_for_user(user, kind=kind, limit=limit)}
    payload.update(run_meta())
    return Response(payload)


@api_view(["POST"])
def recommendations_refresh(request):
    user = current_user(request)
    backfill_features()
    count = build_profile(user)
    payload = {"rebuilt_preferences": count}
    payload.update(run_meta())
    return Response(payload)
