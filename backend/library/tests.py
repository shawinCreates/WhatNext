from django.test import TestCase
from rest_framework.test import APIClient

from catalog.services import upsert_movie, upsert_show

MOVIE_PAYLOAD = {
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
    "genres": [{"id": 18, "name": "Drama"}],
}

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


class MovieRatingNoteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        movie = upsert_movie(MOVIE_PAYLOAD)
        response = self.client.post(
            "/api/v1/library",
            {"movie_id": movie.id, "status": "WATCHED"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.entry_id = response.data["id"]

    def test_patch_rating_and_note(self):
        response = self.client.patch(
            f"/api/v1/library/items/{self.entry_id}",
            {"rating": 9, "personal_note": "  Great ending  "},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rating"], 9)
        self.assertEqual(response.data["personal_note"], "Great ending")

    def test_rating_bounds_rejected(self):
        for bad in (0, 11, 0.9, 10.1):
            response = self.client.patch(
                f"/api/v1/library/items/{self.entry_id}",
                {"rating": bad},
                format="json",
            )
            self.assertEqual(response.status_code, 400)

    def test_decimal_rating_stored_and_rounded(self):
        response = self.client.patch(
            f"/api/v1/library/items/{self.entry_id}",
            {"rating": 9.6},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rating"], 9.6)

        response = self.client.patch(
            f"/api/v1/library/items/{self.entry_id}",
            {"rating": 8.24},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rating"], 8.2)

    def test_rating_can_be_cleared(self):
        self.client.patch(
            f"/api/v1/library/items/{self.entry_id}", {"rating": 7}, format="json"
        )
        response = self.client.patch(
            f"/api/v1/library/items/{self.entry_id}",
            {"rating": None},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["rating"])

    def test_oversize_note_rejected(self):
        response = self.client.patch(
            f"/api/v1/library/items/{self.entry_id}",
            {"personal_note": "x" * 2001},
            format="json",
        )

        self.assertEqual(response.status_code, 400)


class ShowRatingNoteTests(TestCase):
    def test_show_rating_bounds(self):
        client = APIClient()
        show = upsert_show(SHOW_PAYLOAD)
        created = client.post(
            "/api/v1/library/shows",
            {"show_id": show.id, "status": "WATCHED", "rating": 8},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["rating"], 8)

        bad = client.patch(
            f"/api/v1/library/shows/items/{created.data['id']}",
            {"rating": 11},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)
