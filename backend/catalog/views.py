from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Movie, Show
from .serializers import ImportMovieSerializer, MovieSerializer, ShowSerializer
from .services import (
    SECTIONS,
    TMDBError,
    anime_section,
    credits,
    director_of,
    genre_list,
    get_movie,
    get_show,
    movie_section,
    search_movies,
    search_shows,
    season_detail,
    show_section,
    similar,
    trending_movies,
    upsert_movie,
    upsert_show,
    videos,
)


@api_view(["GET"])
def search(request):
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response({"results": []})
    try:
        results = search_movies(query)
    except TMDBError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response({"results": results})


@api_view(["POST"])
def import_movie(request):
    serializer = ImportMovieSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    tmdb_id = serializer.validated_data["tmdb_id"]
    try:
        payload = get_movie(tmdb_id)
    except TMDBError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    movie = upsert_movie(payload, director=director_of("movie", tmdb_id))
    from taste.services import backfill_title

    backfill_title(movie=movie)
    return Response(MovieSerializer(movie).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def movies_list(request):
    movies = Movie.objects.prefetch_related("genres").order_by("-updated_at")[:60]
    return Response(MovieSerializer(movies, many=True).data)


@api_view(["GET"])
def movie_detail(request, pk):
    try:
        movie = Movie.objects.prefetch_related("genres").get(pk=pk)
    except Movie.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(MovieSerializer(movie).data)


@api_view(["GET"])
def trending(request):
    try:
        results = trending_movies()
    except TMDBError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response({"results": results})


def _page_param(request):
    try:
        page = int(request.query_params.get("page", 1))
    except (TypeError, ValueError):
        return None
    return page if page >= 1 else None


def _section_response(section, genre, fetch):
    if section not in SECTIONS or (section == "genre" and not genre):
        return Response(
            {"detail": f"section must be one of {sorted(SECTIONS)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        return Response({"results": fetch()})
    except TMDBError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


def _paged_section_response(request, fetch):
    page = _page_param(request)
    if page is None:
        return Response(
            {"detail": "page must be a positive integer"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    section = request.query_params.get("section", "trending")
    genre = request.query_params.get("genre")
    return _section_response(section, genre, lambda: fetch(section, genre, page))


@api_view(["GET"])
def movies_browse(request):
    if request.query_params.get("section", "trending") == "awarded":
        # Curated seed (see seed_awards) — DB-first, no TMDB heuristic.
        awarded = (
            Movie.objects.exclude(award_label="")
            .prefetch_related("genres")
            .order_by("title")
        )
        return Response(MovieSerializer(awarded, many=True).data)
    return _paged_section_response(request, movie_section)


@api_view(["GET"])
def shows_browse(request):
    return _paged_section_response(request, show_section)


@api_view(["GET"])
def anime_browse(request):
    return _paged_section_response(request, anime_section)


@api_view(["GET"])
def genres(request):
    media = request.query_params.get("media", "movie")
    if media not in ("movie", "tv"):
        return Response(
            {"detail": "media must be 'movie' or 'tv'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        return Response({"genres": genre_list(media)})
    except TMDBError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def shows_search(request):
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response({"results": []})
    try:
        results = search_shows(query)
    except TMDBError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response({"results": results})


@api_view(["POST"])
def import_show(request):
    serializer = ImportMovieSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        payload = get_show(serializer.validated_data["tmdb_id"])
    except TMDBError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    show = upsert_show(payload)
    from taste.services import backfill_title

    backfill_title(show=show)
    return Response(ShowSerializer(show).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def shows_list(request):
    shows = Show.objects.prefetch_related("genres").order_by("-updated_at")[:60]
    return Response(ShowSerializer(shows, many=True).data)


@api_view(["GET"])
def show_detail(request, pk):
    try:
        show = Show.objects.prefetch_related("genres").get(pk=pk)
    except Show.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(ShowSerializer(show).data)


def _tmdb_detail_proxy(request, media, tmdb_id, fetch):
    try:
        tmdb_id = int(tmdb_id)
    except (TypeError, ValueError):
        return Response(
            {"detail": "tmdb id must be an integer"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if media not in ("movie", "tv"):
        return Response(
            {"detail": "media must be 'movie' or 'tv'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        return Response(fetch(media, tmdb_id))
    except TMDBError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def title_videos(request, media, tmdb_id):
    return _tmdb_detail_proxy(request, media, tmdb_id, lambda m, i: {"results": videos(m, i)})


@api_view(["GET"])
def title_credits(request, media, tmdb_id):
    return _tmdb_detail_proxy(request, media, tmdb_id, credits)


@api_view(["GET"])
def title_similar(request, media, tmdb_id):
    return _tmdb_detail_proxy(request, media, tmdb_id, lambda m, i: {"results": similar(m, i)})


@api_view(["GET"])
def tv_season(request, tmdb_id, season):
    try:
        tmdb_id, season = int(tmdb_id), int(season)
    except (TypeError, ValueError):
        return Response(
            {"detail": "ids must be integers"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if season < 0:
        return Response(
            {"detail": "season must be 0 or greater"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        return Response(season_detail(tmdb_id, season))
    except TMDBError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
