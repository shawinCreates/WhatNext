import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

from .models import Genre, Movie, Show

ANIME_GENRE_ID = 16
ANIME_ORIGIN = "JP"


class TMDBError(Exception):
    """Raised when a TMDB request fails or the API key is missing."""


def _get(path, **params):
    if not settings.TMDB_API_KEY:
        raise TMDBError("TMDB_API_KEY is not set")
    params["api_key"] = settings.TMDB_API_KEY
    url = f"{settings.TMDB_BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise TMDBError(f"TMDB request failed ({exc.code}) for {path}") from exc
    except urllib.error.URLError as exc:
        raise TMDBError(f"TMDB request failed: {exc.reason}") from exc


def search_movies(query, page=1):
    data = _get("/search/movie", query=query, page=page, include_adult="false")
    return data.get("results", [])


def get_movie(tmdb_id):
    return _get(f"/movie/{tmdb_id}")


def trending_movies(page=1):
    data = _get("/trending/movie/week", page=page, include_adult="false")
    return data.get("results", [])


def discover(media, **params):
    """Thin proxy over TMDB /discover/{movie,tv}; returns raw results."""
    params.setdefault("include_adult", "false")
    params.setdefault("page", 1)
    data = _get(f"/discover/{media}", **params)
    return data.get("results", [])


def genre_list(media):
    data = _get(f"/genre/{media}/list")
    return data.get("genres", [])


def search_shows(query, page=1):
    data = _get("/search/tv", query=query, page=page, include_adult="false")
    return data.get("results", [])


def get_show(tmdb_id):
    return _get(f"/tv/{tmdb_id}")


def trending_tv(page=1):
    data = _get("/trending/tv/week", page=page, include_adult="false")
    return data.get("results", [])


SECTIONS = ("trending", "latest", "upcoming", "top_rated", "awarded", "genre")


def movie_section(section, genre_id=None, page=1):
    if section == "trending":
        return trending_movies(page=page)
    if section == "latest":
        return _get("/movie/now_playing", page=page, include_adult="false").get("results", [])
    if section == "upcoming":
        return _get("/movie/upcoming", page=page, include_adult="false").get("results", [])
    if section == "top_rated":
        return _get("/movie/top_rated", page=page, include_adult="false").get("results", [])
    if section == "awarded":
        # shortcut: TMDB has no awards data; acclaimed ≈ high average + many votes.
        return discover(
            "movie",
            sort_by="vote_average.desc",
            vote_count_gte=1000,
            vote_average_gte=7.0,
            page=page,
        )
    if section == "genre" and genre_id:
        return discover(
            "movie", with_genres=genre_id, sort_by="popularity.desc", page=page
        )
    raise TMDBError(f"Unknown movie section: {section}")


def show_section(section, genre_id=None, page=1):
    if section == "trending":
        return trending_tv(page=page)
    if section == "latest":
        return _get("/tv/airing_today", page=page, include_adult="false").get("results", [])
    if section == "upcoming":
        return discover(
            "tv",
            sort_by="first_air_date.asc",
            first_air_date_gte=_today(),
            vote_count_gte=5,
            page=page,
        )
    if section == "top_rated":
        return _get("/tv/top_rated", page=page, include_adult="false").get("results", [])
    if section == "awarded":
        # shortcut: see movie_section.
        return discover(
            "tv",
            sort_by="vote_average.desc",
            vote_count_gte=500,
            vote_average_gte=7.5,
            page=page,
        )
    if section == "genre" and genre_id:
        return discover("tv", with_genres=genre_id, sort_by="popularity.desc", page=page)
    raise TMDBError(f"Unknown show section: {section}")


def anime_section(section, genre_id=None, page=1):
    base = {"with_genres": ANIME_GENRE_ID, "with_origin_country": ANIME_ORIGIN}
    if section == "trending":
        if page != 1:
            return [
                r
                for r in trending_tv(page=page)
                if ANIME_GENRE_ID in (r.get("genre_ids") or [])
                and ANIME_ORIGIN in (r.get("origin_country") or [])
            ]
        return [
            r
            for r in trending_tv()
            if ANIME_GENRE_ID in (r.get("genre_ids") or [])
            and ANIME_ORIGIN in (r.get("origin_country") or [])
        ][:12]
    if section == "latest":
        return discover(
            "tv",
            sort_by="first_air_date.desc",
            first_air_date_lte=_today(),
            vote_count_gte=10,
            page=page,
            **base,
        )
    if section == "upcoming":
        return discover(
            "tv", sort_by="first_air_date.asc", first_air_date_gte=_today(), page=page, **base
        )
    if section == "top_rated":
        return discover(
            "tv", sort_by="vote_average.desc", vote_count_gte=100, page=page, **base
        )
    if section == "awarded":
        # shortcut: see movie_section.
        return discover(
            "tv",
            sort_by="vote_average.desc",
            vote_count_gte=200,
            vote_average_gte=8.0,
            page=page,
            **base,
        )
    if section == "genre" and genre_id:
        return discover(
            "tv",
            with_genres=f"{ANIME_GENRE_ID},{genre_id}",
            sort_by="popularity.desc",
            with_origin_country=ANIME_ORIGIN,
            page=page,
        )
    raise TMDBError(f"Unknown anime section: {section}")


def _today():
    from datetime import date

    return date.today().isoformat()


def videos(media, tmdb_id):
    """Trailer/teaser clips for a TMDB movie or TV entry."""
    data = _get(f"/{media}/{tmdb_id}/videos")
    return data.get("results", [])


def credits(media, tmdb_id):
    """Cast and crew for a TMDB movie or TV entry."""
    return _get(f"/{media}/{tmdb_id}/credits")


def similar(media, tmdb_id, page=1):
    """TMDB's own similar titles for a movie or TV entry."""
    data = _get(f"/{media}/{tmdb_id}/similar", page=page, include_adult="false")
    return data.get("results", [])


def _sync_genres(payload):
    genres = []
    for genre in payload.get("genres", []):
        obj, _ = Genre.objects.update_or_create(
            tmdb_id=genre["id"], defaults={"name": genre["name"]}
        )
        genres.append(obj)
    return genres


def _year_of(date_value):
    return int(date_value[:4]) if date_value else None


def upsert_show(payload):
    """Create or update a Show from a TMDB TV payload; auto-flags anime."""
    first_air = payload.get("first_air_date") or None
    genre_names = [g.get("name") for g in payload.get("genres", [])]
    is_anime = "Animation" in genre_names and (
        payload.get("original_language") == "ja"
        or ANIME_ORIGIN in (payload.get("origin_country") or [])
    )
    show, _ = Show.objects.update_or_create(
        tmdb_id=payload["id"],
        defaults={
            "name": payload.get("name") or payload.get("original_name") or "",
            "original_name": payload.get("original_name") or "",
            "first_air_date": first_air,
            "release_year": _year_of(first_air),
            "overview": payload.get("overview") or "",
            "original_language": payload.get("original_language") or "",
            "poster_path": payload.get("poster_path") or "",
            "backdrop_path": payload.get("backdrop_path") or "",
            "seasons": payload.get("number_of_seasons"),
            "episodes": payload.get("number_of_episodes"),
            "is_anime": is_anime,
            "tagline": payload.get("tagline") or "",
            "vote_average": payload.get("vote_average"),
            "vote_count": payload.get("vote_count"),
        },
    )
    show.genres.set(_sync_genres(payload))
    return show


def upsert_movie(payload):
    """Create or update a Movie (and its Genres) from a TMDB payload."""
    release_date = payload.get("release_date") or None
    movie, _ = Movie.objects.update_or_create(
        tmdb_id=payload["id"],
        defaults={
            "imdb_id": payload.get("imdb_id") or None,
            "title": payload.get("title") or payload.get("original_title") or "",
            "original_title": payload.get("original_title") or "",
            "release_date": release_date,
            "release_year": _year_of(release_date),
            "runtime": payload.get("runtime") or None,
            "overview": payload.get("overview") or "",
            "original_language": payload.get("original_language") or "",
            "poster_path": payload.get("poster_path") or "",
            "backdrop_path": payload.get("backdrop_path") or "",
            "tagline": payload.get("tagline") or "",
            "vote_average": payload.get("vote_average"),
            "vote_count": payload.get("vote_count"),
        },
    )
    movie.genres.set(_sync_genres(payload))
    return movie
