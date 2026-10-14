from rest_framework.decorators import api_view
from rest_framework.response import Response

from library.views import current_user

from .services import profile_payload


@api_view(["GET"])
def taste_profile(request):
    return Response(profile_payload(current_user(request)))
