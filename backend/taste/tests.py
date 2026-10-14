from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Genre, Movie
from library.models import UserMovie
from taste.models import MovieFeature, UserPreference
from taste.services import backfill_features, build_profile
from taste.taxonomy import FEATURES, GENRE_FEATURES, GROUPS, rating_weight


_GENRE_IDS = {}


def make_movie(tmdb_id, title, genres):
    def genre_obj(name):
        if name not in _GENRE_IDS:
            _GENRE_IDS[name] = 9000 + len(_GENRE_IDS)
        return Genre.objects.get_or_create(
            tmdb_id=_GENRE_IDS[name], defaults={"name": name}
        )[0]

    movie = Movie.objects.create(tmdb_id=tmdb_id, title=title)
    movie.genres.set(genre_obj(g) for g in genres)
    return movie


class TaxonomyTests(TestCase):
    def test_keys_have_known_groups_and_labels(self):
        self.assertGreaterEqual(len(FEATURES), 20)
        for key, (group, label, description) in FEATURES.items():
            self.assertIn(group, GROUPS)
            self.assertTrue(label and description)

    def test_genre_priors_reference_known_features(self):
        for genre, priors in GENRE_FEATURES.items():
            for key, value in priors.items():
                self.assertIn(key, FEATURES)
                self.assertGreater(value, 0)
                self.assertLessEqual(value, 1)

    def test_rating_buckets(self):
        self.assertEqual(rating_weight(9.6), 1.0)
        self.assertEqual(rating_weight(8.2), 0.5)
        self.assertEqual(rating_weight(7.6), 0.15)
        self.assertEqual(rating_weight(6.8), -0.5)


class ProfileTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username="owner")
        self.drama = make_movie(1, "Drama Film", ["Drama"])
        self.comedy = make_movie(2, "Comedy Film", ["Comedy"])
        backfill_features()

    def rate(self, movie, rating, favorite=False):
        return UserMovie.objects.create(
            user=self.user, movie=movie, status="WATCHED",
            rating=rating, is_favorite=favorite,
        )

    def test_backfill_is_idempotent(self):
        created, updated = backfill_features()
        self.assertEqual(created, 0)
        self.assertGreater(updated, 0)
        self.assertEqual(
            MovieFeature.objects.filter(movie=self.drama).count(), 3
        )  # Drama priors

    def test_build_profile_math(self):
        self.rate(self.drama, 9)  # scale 1.0 -> depth .6*.5=.3
        self.rate(self.comedy, 6.5)  # scale -0.5 -> wit .7*.5*-.5=-.175
        self.assertEqual(build_profile(self.user), 6)

        depth = UserPreference.objects.get(
            user=self.user, feature_key="character_depth"
        )
        self.assertEqual(depth.polarity, 1)
        self.assertAlmostEqual(depth.weight, 0.3)
        self.assertAlmostEqual(depth.confidence, 0.2)  # 1 title of 5

        wit = UserPreference.objects.get(user=self.user, feature_key="wit")
        self.assertEqual(wit.polarity, -1)
        self.assertAlmostEqual(wit.weight, 0.175)

    def test_hiding_a_top_title_moves_its_features(self):
        entry = self.rate(self.drama, 9.6, favorite=True)
        self.rate(self.comedy, 8.0)
        build_profile(self.user)
        before = UserPreference.objects.get(
            user=self.user, feature_key="character_depth"
        ).weight

        entry.rating = None
        entry.save()
        build_profile(self.user)
        # Its only evidence gone: the preference disappears entirely.
        self.assertFalse(
            UserPreference.objects.filter(
                user=self.user, feature_key="character_depth"
            ).exists()
        )

    def test_profile_api_shape(self):
        self.rate(self.drama, 9)
        response = APIClient().get("/api/v1/taste/profile")

        self.assertEqual(response.status_code, 200)
        self.assertIn("positive", response.data)
        self.assertIn("negative", response.data)
        self.assertIn("generated_at", response.data)
        top = response.data["positive"][0]
        self.assertEqual(top["feature"], "character_depth")
        self.assertEqual(top["strength"], "emerging")  # 1 title < 3
        self.assertEqual(top["titles"][0]["title"], "Drama Film")
        self.assertEqual(top["titles"][0]["rating"], 9)
