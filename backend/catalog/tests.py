from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Genre, Movie
from catalog.services import upsert_movie, upsert_show

SAMPLE_PAYLOAD = {
    "id": 550,
    "imdb_id": "tt0137523",
    "title": "Fight Club",
    "original_title": "Fight Club",
    "release_date": "1999-10-15",
    "runtime": 139,
    "overview": "An insomniac office worker and a soap salesman...",
    "original_language": "en",
    "poster_path": "/poster.jpg",
    "backdrop_path": "/backdrop.jpg",
    "genres": [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}],
}


class UpsertMovieTests(TestCase):
    def test_maps_fields_and_genres(self):
        movie = upsert_movie(SAMPLE_PAYLOAD)

        self.assertEqual(movie.tmdb_id, 550)
        self.assertEqual(movie.title, "Fight Club")
        self.assertEqual(movie.release_year, 1999)
        self.assertEqual(movie.imdb_id, "tt0137523")
        self.assertEqual(movie.runtime, 139)
        self.assertEqual(
            set(movie.genres.values_list("name", flat=True)), {"Drama", "Thriller"}
        )

    def test_handles_missing_release_date(self):
        movie = upsert_movie({**SAMPLE_PAYLOAD, "id": 1, "release_date": ""})

        self.assertIsNone(movie.release_date)
        self.assertIsNone(movie.release_year)

    def test_reimport_updates_in_place(self):
        upsert_movie(SAMPLE_PAYLOAD)
        updated = upsert_movie({**SAMPLE_PAYLOAD, "title": "Fight Club (2000)"})

        self.assertEqual(Movie.objects.count(), 1)
        self.assertEqual(Genre.objects.count(), 2)
        self.assertEqual(updated.title, "Fight Club (2000)")


class MovieViewTests(TestCase):
    def test_list_returns_stored_movies(self):
        upsert_movie(SAMPLE_PAYLOAD)

        response = APIClient().get("/api/v1/movies")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["backdrop_path"], "/backdrop.jpg")

    def test_detail_404_for_missing_movie(self):
        response = APIClient().get("/api/v1/movies/9999")

        self.assertEqual(response.status_code, 404)

    @patch("catalog.views.trending_movies")
    def test_trending_proxies_results(self, mock_trending):
        mock_trending.return_value = [{"id": 550, "title": "Fight Club"}]

        response = APIClient().get("/api/v1/movies/trending")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["title"], "Fight Club")

    def test_browse_rejects_unknown_section(self):
        response = APIClient().get("/api/v1/shows/browse?section=nope")

        self.assertEqual(response.status_code, 400)

    def test_browse_rejects_bad_page(self):
        response = APIClient().get("/api/v1/movies/browse?section=trending&page=0")

        self.assertEqual(response.status_code, 400)

    def test_genres_rejects_unknown_media(self):
        response = APIClient().get("/api/v1/genres?media=book")

        self.assertEqual(response.status_code, 400)


SHOW_PAYLOAD = {
    "id": 1399,
    "name": "Game of Thrones",
    "original_name": "Game of Thrones",
    "first_air_date": "2011-04-17",
    "overview": "Seven noble families fight...",
    "original_language": "en",
    "origin_country": ["US"],
    "poster_path": "/poster.jpg",
    "backdrop_path": "/backdrop.jpg",
    "number_of_seasons": 8,
    "number_of_episodes": 73,
    "genres": [{"id": 18, "name": "Drama"}],
}

ANIME_PAYLOAD = {
    **SHOW_PAYLOAD,
    "id": 12971,
    "name": "Cowboy Bebop",
    "original_language": "ja",
    "origin_country": ["JP"],
    "genres": [{"id": 16, "name": "Animation"}, {"id": 18, "name": "Drama"}],
}


class UpsertShowTests(TestCase):
    def test_maps_fields_and_flags_anime(self):
        drama = upsert_show(SHOW_PAYLOAD)
        anime = upsert_show(ANIME_PAYLOAD)

        self.assertEqual(drama.release_year, 2011)
        self.assertFalse(drama.is_anime)
        self.assertTrue(anime.is_anime)
        self.assertEqual(anime.seasons, 8)


class AwardedBrowseTests(TestCase):
    def test_awarded_serves_curated_movies(self):
        upsert_movie({**SAMPLE_PAYLOAD, "id": 550})
        movie = Movie.objects.get(tmdb_id=550)
        movie.award_label = "Oscar · Best Picture 2020"
        movie.save()

        response = APIClient().get("/api/v1/movies/browse?section=awarded")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["award_label"], "Oscar · Best Picture 2020")

    def test_awarded_excludes_unlabelled(self):
        upsert_movie({**SAMPLE_PAYLOAD, "id": 550})

        response = APIClient().get("/api/v1/movies/browse?section=awarded")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])


class TitleProxyTests(TestCase):
    def test_rejects_bad_media_and_id(self):
        client = APIClient()

        self.assertEqual(client.get("/api/v1/tmdb/book/550/videos").status_code, 400)
        self.assertEqual(client.get("/api/v1/tmdb/movie/nope/videos").status_code, 400)

    @patch("catalog.views.videos")
    def test_videos_shape(self, mock_videos):
        mock_videos.return_value = [{"key": "abc", "site": "YouTube", "type": "Trailer"}]

        response = APIClient().get("/api/v1/tmdb/movie/550/videos")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["key"], "abc")

    def test_season_rejects_negative(self):
        # Django's int converter never routes negatives — 404, not 400.
        response = APIClient().get("/api/v1/tmdb/tv/1399/season/-1")

        self.assertEqual(response.status_code, 404)

    @patch("catalog.views.season_detail")
    def test_season_shape(self, mock_season):
        mock_season.return_value = {"season_number": 1, "episodes": []}

        response = APIClient().get("/api/v1/tmdb/tv/1399/season/1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["episodes"], [])
