from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import UserMovie, UserShow
from .serializers import UserMovieSerializer, UserShowSerializer

User = get_user_model()


def _rebuild_profile(user):
    from taste.services import build_profile

    build_profile(user)


def current_user(request):
    # ponytail: single-user assumption. Swap for request.user when auth is added.
    if request.user.is_authenticated:
        return request.user
    user, _ = User.objects.get_or_create(
        username="owner", defaults={"is_staff": True, "is_superuser": True}
    )
    return user


@api_view(["GET", "POST"])
def library(request):
    user = current_user(request)

    if request.method == "POST":
        serializer = UserMovieSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movie = serializer.validated_data.pop("movie")
        data = {k: v for k, v in serializer.validated_data.items()}
        entry, created = UserMovie.objects.update_or_create(
            user=user, movie=movie, defaults=data
        )
        _rebuild_profile(user)
        return Response(
            UserMovieSerializer(entry).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    entries = UserMovie.objects.filter(user=user).select_related("movie")
    return Response(UserMovieSerializer(entries, many=True).data)


@api_view(["PATCH", "DELETE"])
def library_item(request, pk):
    user = current_user(request)
    try:
        entry = UserMovie.objects.get(pk=pk, user=user)
    except UserMovie.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        entry.delete()
        _rebuild_profile(user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = UserMovieSerializer(entry, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    _rebuild_profile(user)
    return Response(serializer.data)


@api_view(["GET", "POST"])
def shows_library(request):
    user = current_user(request)

    if request.method == "POST":
        serializer = UserShowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        show = serializer.validated_data.pop("show")
        data = {k: v for k, v in serializer.validated_data.items()}
        entry, created = UserShow.objects.update_or_create(
            user=user, show=show, defaults=data
        )
        _rebuild_profile(user)
        return Response(
            UserShowSerializer(entry).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    entries = UserShow.objects.filter(user=user).select_related("show")
    return Response(UserShowSerializer(entries, many=True).data)


@api_view(["PATCH", "DELETE"])
def shows_library_item(request, pk):
    user = current_user(request)
    try:
        entry = UserShow.objects.get(pk=pk, user=user)
    except UserShow.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        entry.delete()
        _rebuild_profile(user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = UserShowSerializer(entry, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    _rebuild_profile(user)
    return Response(serializer.data)
