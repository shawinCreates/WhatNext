from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from rest_framework.test import APIClient

import random

from catalog.models import Genre, Movie, Show
from library.models import UserMovie
from taste.management.commands import eval_reco
from taste.models import MovieFeature, RecoServe, UserPreference
from taste.reco import (
    _cosine,
    _feature_map,
    _own_ratings,
    _quality,
    predict_rating,
    recommend_for_user,
    similar_for_title,
)
from taste.services import backfill_features, build_profile
from taste.taxonomy import FEATURES, GENRE_FEATURES, GROUPS, rating_weight
from unittest.mock import patch


_GENRE_IDS = {}


def _genre_obj(name):
    if name not in _GENRE_IDS:
        _GENRE_IDS[name] = 9000 + len(_GENRE_IDS)
    return Genre.objects.get_or_create(
        tmdb_id=_GENRE_IDS[name], defaults={"name": name}
    )[0]


def make_movie(tmdb_id, title, genres, director=""):
    movie = Movie.objects.create(
        tmdb_id=tmdb_id, title=title, poster_path=f"/{tmdb_id}.jpg", director=director
    )
    movie.genres.set(_genre_obj(g) for g in genres)
    return movie


def make_show(tmdb_id, name, genres):
    show = Show.objects.create(
        tmdb_id=tmdb_id, name=name, poster_path=f"/{tmdb_id}.jpg"
    )
    show.genres.set(_genre_obj(g) for g in genres)
    return show


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


class RecoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username="owner")
        self.drama = make_movie(11, "Liked Drama", ["Drama"])
        self.drama2 = make_movie(12, "Unseen Drama", ["Drama"])
        self.horror = make_movie(13, "Unseen Horror", ["Horror"])
        backfill_features()
        UserMovie.objects.create(
            user=self.user, movie=self.drama, status="WATCHED", rating=9.5
        )
        build_profile(self.user)

    def test_excludes_library_titles(self):
        results = recommend_for_user(self.user, limit=10)
        titles = {r["title"] for r in results}
        self.assertNotIn("Liked Drama", titles)
        self.assertIn("Unseen Drama", titles)

    def test_prefers_taste_and_genre_match(self):
        results = recommend_for_user(self.user, limit=10, jitter=False)
        self.assertGreaterEqual(len(results), 2)
        # Same genre + shared taste features outrank unrelated horror.
        self.assertEqual(results[0]["title"], "Unseen Drama")
        self.assertEqual([r["rank"] for r in results], list(range(1, len(results) + 1)))

    def test_explanations_reference_stored_signals(self):
        results = recommend_for_user(self.user, limit=10, jitter=False)
        top = results[0]
        self.assertTrue(top["personalized"])
        self.assertGreater(len(top["reasons"]), 0)
        for reason in top["reasons"]:
            self.assertIn(reason["feature"], FEATURES)
        for similar in top["similar_liked"]:
            self.assertEqual(similar["title"], "Liked Drama")

    def test_cold_start_is_not_personalized(self):
        User = get_user_model()
        cold, _ = User.objects.get_or_create(username="cold")
        results = recommend_for_user(cold, limit=5)
        self.assertTrue(results)  # quality-ranked fallback, honest flag
        self.assertFalse(results[0]["personalized"])
        self.assertEqual(results[0]["reasons"], [])

    def test_cosine_basics(self):
        self.assertAlmostEqual(_cosine({"a": 1.0}, {"a": 1.0}), 1.0)
        self.assertAlmostEqual(_cosine({"a": 1.0}, {"b": 1.0}), 0.0)

    def test_recommendations_api_shape(self):
        client = APIClient()
        response = client.get("/api/v1/recommendations?limit=5")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertIn("algorithm_version", response.data)
        self.assertIn("generated_at", response.data)
        item = response.data["results"][0]
        for key in (
            "title",
            "score",
            "rank",
            "reasons",
            "similar_liked",
            "genres",
            "award_label",
            "created_by",
            "runtime",
            "seasons",
            "episodes",
            "is_anime",
            "original_language",
            "vote_count",
        ):
            self.assertIn(key, item)

    def test_refresh_rebuilds_profile(self):
        response = APIClient().post("/api/v1/recommendations/refresh")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data["rebuilt_preferences"], 0)


class RotationTests(TestCase):
    """Jitter + serve rotation: pick lists stay fresh across requests."""

    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username="owner")
        self.pool = [make_movie(41 + i, f"Drift Film {i}", ["Drama"]) for i in range(6)]
        backfill_features()

    def test_second_request_rotates_past_recent_serves(self):
        client = APIClient()
        first = client.get("/api/v1/recommendations?limit=3").data["results"]
        second = client.get("/api/v1/recommendations?limit=3").data["results"]
        self.assertEqual(len(first), 3)
        self.assertEqual(len(second), 3)
        ids1 = {(r["kind"], r["id"]) for r in first}
        ids2 = {(r["kind"], r["id"]) for r in second}
        self.assertFalse(ids1 & ids2)
        self.assertEqual(len(ids1 | ids2), 6)  # pool exhausts before relaxation

    def test_jitter_is_deterministic_per_seed(self):
        random.seed(11)
        first = [r["score"] for r in recommend_for_user(self.user, limit=5)]
        random.seed(11)
        second = [r["score"] for r in recommend_for_user(self.user, limit=5)]
        self.assertEqual(first, second)


class ShowQuotaTests(TestCase):
    """kind="all" keeps series on the shelf even when movies outscore them."""

    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username="owner")
        self.dramas = [make_movie(61 + i, f"Loved Drama {i}", ["Drama"]) for i in range(3)]
        self.dramas += [
            make_movie(64 + i, f"Unseen Drama {i}", ["Drama"]) for i in range(3)
        ]
        self.show = make_show(70, "Horror Series", ["Horror"])
        backfill_features()
        for movie in self.dramas[:3]:
            UserMovie.objects.create(
                user=self.user, movie=movie, status="WATCHED", rating=9.0
            )
        build_profile(self.user)

    def test_quota_slots_a_show_into_a_movie_dominated_page(self):
        results = recommend_for_user(self.user, jitter=False, limit=3)
        kinds = [r["kind"] for r in results]
        self.assertIn("show", kinds)
        self.assertEqual(kinds.count("show"), 1)


class SimilarTests(TestCase):
    """'More like this': local content-based neighbours, TMDB as fallback."""

    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username="owner")
        self.target = make_movie(81, "Anchor Thriller", ["Thriller", "Drama"])
        self.neighbour = make_movie(82, "Neighbour Thriller", ["Thriller"])
        make_movie(83, "Unrelated Horror", ["Horror"])
        self.shelved = make_movie(84, "Shelved Thriller", ["Thriller"])
        backfill_features()
        UserMovie.objects.create(
            user=self.user, movie=self.shelved, status="WATCHED", rating=9.0
        )

    def test_local_neighbours_rank_first_and_library_is_excluded(self):
        results = similar_for_title(self.user, "movie", self.target, limit=12)
        titles = [r["title"] for r in results]
        self.assertTrue(all(r["local"] for r in results))
        self.assertEqual(results[0]["title"], "Neighbour Thriller")
        self.assertNotIn("Anchor Thriller", titles)
        self.assertNotIn("Shelved Thriller", titles)

    def test_view_tops_up_from_tmdb_when_local_is_thin(self):
        tmdb_extra = {
            "id": 999,
            "title": "TMDB Thriller",
            "release_date": "2020-01-01",
            "poster_path": "/p.jpg",
        }
        with patch("catalog.services.similar", return_value=[tmdb_extra]):
            response = APIClient().get(
                f"/api/v1/taste/similar/movie/{self.target.id}?limit=12"
            )
        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        self.assertEqual(
            [r["title"] for r in results],
            ["Neighbour Thriller", "Unrelated Horror", "TMDB Thriller"],
        )
        fallback = next(r for r in results if not r["local"])
        self.assertEqual(fallback["tmdb_id"], 999)
        self.assertEqual(fallback["title"], "TMDB Thriller")
        self.assertEqual(fallback["year"], 2020)

    def test_bad_kind_is_400(self):
        response = APIClient().get(f"/api/v1/taste/similar/anime/{self.target.id}")
        self.assertEqual(response.status_code, 400)


class DirectorAffinityTests(TestCase):
    """Entity affinity: your rated directors lift their other titles."""

    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username="owner")
        self.liked = make_movie(91, "Liked Drama", ["Drama"], director="Denis Villeneuve")
        self.same = make_movie(92, "Same Director Drama", ["Drama"], director="Denis Villeneuve")
        self.other = make_movie(93, "Other Director Drama", ["Drama"], director="Greta Gerwig")
        backfill_features()
        UserMovie.objects.create(
            user=self.user, movie=self.liked, status="WATCHED", rating=9.5
        )
        build_profile(self.user)

    def test_same_director_outranks_other(self):
        results = recommend_for_user(self.user, jitter=False, limit=5)
        self.assertEqual(results[0]["title"], "Same Director Drama")


class RejectionSignalTests(TestCase):
    """'Not for me' feeds negative evidence into the profile (Phase 5)."""

    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username="owner")
        self.drama = make_movie(96, "Deep Drama", ["Drama"])
        self.horror = make_movie(97, "Horror Reject", ["Horror"])
        backfill_features()
        UserMovie.objects.create(
            user=self.user, movie=self.drama, status="WATCHED", rating=9.0
        )
        UserMovie.objects.create(
            user=self.user, movie=self.horror, status="REJECTED"
        )  # unrated, still negative
        build_profile(self.user)

    def test_rejected_genre_moves_negative_rated_moves_positive(self):
        unease = UserPreference.objects.get(user=self.user, feature_key="unease")
        self.assertEqual(unease.polarity, -1)
        self.assertGreater(unease.weight, 0)
        depth = UserPreference.objects.get(user=self.user, feature_key="character_depth")
        self.assertEqual(depth.polarity, 1)


class FeedbackTests(TestCase):
    """Serve log powers the funnel (docs §6) and self-prunes."""

    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username="owner")
        self.pool = [make_movie(101 + i, f"Funnel Film {i}", ["Drama"]) for i in range(3)]
        backfill_features()

    def test_feedback_counts_later_actions(self):
        client = APIClient()
        served = client.get("/api/v1/recommendations?limit=2").data["results"]
        self.assertEqual(len(served), 2)
        client.post(
            "/api/v1/library",
            data={"movie_id": served[0]["id"], "status": "WATCHED"},
            format="json",
        )
        client.post(
            "/api/v1/library",
            data={"movie_id": served[1]["id"], "status": "REJECTED"},
            format="json",
        )
        stats = client.get("/api/v1/recommendations/feedback").data
        self.assertEqual(stats["served"], 2)
        self.assertEqual(stats["watched"], 1)
        self.assertEqual(stats["rejected"], 1)
        self.assertEqual(stats["conversion"], 0.5)

    def test_empty_feedback_is_zeroed(self):
        client = APIClient()
        stats = client.get("/api/v1/recommendations/feedback").data
        self.assertEqual(stats["served"], 0)
        self.assertIsNone(stats["conversion"])

    def test_log_serves_prunes_old_rows(self):
        old = RecoServe.objects.create(user=self.user, tkey="m9999")
        RecoServe.objects.update(served_at=timezone.now() - timedelta(days=120))
        client = APIClient()
        client.get("/api/v1/recommendations?limit=2")
        self.assertFalse(
            RecoServe.objects.filter(pk=old.pk).exists()
        )  # 120-day-old row pruned


class PredictRatingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username="owner")
        self.d1 = make_movie(21, "Predicted Drama A", ["Drama"])
        self.d2 = make_movie(22, "Predicted Drama B", ["Drama"])
        self.horror = make_movie(23, "Predicted Horror", ["Horror"])
        self.unseen = make_movie(24, "Predicted Target", ["Drama"])
        backfill_features()
        for movie, rating in (
            (self.d1, 9.0),
            (self.d2, 8.0),
            (self.horror, 3.0),
        ):
            UserMovie.objects.create(
                user=self.user, movie=movie, status="WATCHED", rating=rating
            )

    def test_similarity_weighted_mean_of_own_ratings(self):
        pred, base, covered = predict_rating(
            self.user, f"m{self.unseen.id}", _feature_map()
        )
        self.assertTrue(covered)
        self.assertAlmostEqual(pred, 8.5)  # equal-similarity neighbors 9.0, 8.0
        self.assertAlmostEqual(base, (9.0 + 8.0 + 3.0) / 3)

    def test_prebuilt_rated_matches_default_path(self):
        features = _feature_map()
        rated = _own_ratings(self.user)
        direct = predict_rating(self.user, f"m{self.unseen.id}", features)
        reused = predict_rating(self.user, f"m{self.unseen.id}", features, rated=rated)
        self.assertAlmostEqual(reused[0], direct[0])

    def test_quality_blends_crowd_and_prediction(self):
        pred_norm = (9.0 - 1) / 9
        self.assertAlmostEqual(_quality(7.0, 9.0, True), 0.5 * 0.7 + 0.5 * pred_norm)
        self.assertAlmostEqual(_quality(7.0, None, False), 0.7)
        self.assertAlmostEqual(_quality(None, None, False), 0.5)

    def test_no_overlap_falls_back_to_mean(self):
        pred, base, covered = predict_rating(
            self.user, f"m{self.horror.id}", _feature_map()
        )
        self.assertFalse(covered)
        self.assertAlmostEqual(pred, base)

    def test_cold_user_predicts_midpoint(self):
        User = get_user_model()
        cold, _ = User.objects.get_or_create(username="cold-user")
        pred, base, covered = predict_rating(
            cold, f"m{self.unseen.id}", _feature_map()
        )
        self.assertFalse(covered)
        self.assertAlmostEqual(pred, 5.5)


class EvalCommandTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username="owner")
        self.dramas = [
            make_movie(31, "Eval Drama One", ["Drama"]),
            make_movie(32, "Eval Drama Two", ["Drama"]),
            make_movie(33, "Eval Drama Three", ["Drama"]),
        ]
        self.horror = make_movie(34, "Eval Horror", ["Horror"])
        backfill_features()
        for movie, rating in zip(
            self.dramas,
            (9.0, 8.5, 9.5),
        ):
            UserMovie.objects.create(
                user=self.user, movie=movie, status="WATCHED", rating=rating
            )
        UserMovie.objects.create(
            user=self.user, movie=self.horror, status="WATCHED", rating=7.0
        )
        build_profile(self.user)

    def test_folds_ranks_and_rolls_back(self):
        pre_entries = sorted(
            UserMovie.objects.values_list("movie_id", "rating")
        )
        pre_prefs = sorted(
            UserPreference.objects.values_list(
                "feature_key", "polarity", "weight"
            )
        )
        summary, _lines = eval_reco.run_eval(self.user)
        self.assertEqual(summary["folds"], 3)  # horror's 7.0 is below threshold
        # Each hidden drama is the only non-library candidate with features,
        # so every fold must surface it at rank 1.
        self.assertEqual(summary["hits"][5], 3)
        self.assertAlmostEqual(summary["mrr"], 1.0)
        self.assertLess(summary["mae"], summary["baseline_mae"])
        # The folded-back database is exactly as it was before the run.
        self.assertEqual(
            sorted(UserMovie.objects.values_list("movie_id", "rating")),
            pre_entries,
        )
        self.assertEqual(
            sorted(
                UserPreference.objects.values_list(
                    "feature_key", "polarity", "weight"
                )
            ),
            pre_prefs,
        )

    def test_command_prints_report(self):
        buffer = StringIO()
        call_command("eval_reco", stdout=buffer)
        output = buffer.getvalue()
        self.assertIn("hit@5", output)
        self.assertIn("MAE", output)
        self.assertIn("folds=3", output)
