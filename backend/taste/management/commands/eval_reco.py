"""Leave-one-out offline eval (Phase 5 A1): ranking + rating error.

For each high-rated library entry: inside an always-rolled-back
transaction, hide the entry, rebuild the taste profile without it, and
run the production recommender on the same code path the API uses.
Reports hit@K / MRR against a popularity baseline and rating MAE / RMSE
against a predict-the-average baseline (08-roadmap-evaluation §§4-5).
The rollback restores the database; interrupting the run is safe.
"""

import math
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Movie, Show
from library.models import UserMovie, UserShow

from taste.reco import (
    ALGORITHM_VERSION,
    FEATURE_VERSION,
    _candidates,
    _cosine,
    _feature_map,
    predict_rating,
    recommend_for_user,
)
from taste.services import build_profile

HIT_KS = (5, 10, 20)
TITLE_KEY = {"movie": "m", "show": "s"}


def _list_diversity(recs, features):
    """Intra-list diversity: 1 minus mean pairwise feature-cosine similarity.

    Higher means the list is more diverse (less redundant). Returns None when
    a list has fewer than two scorable items.
    """
    vecs = []
    for r in recs:
        tkey = TITLE_KEY[r["kind"]] + str(r["id"])
        v = features.get(tkey)
        if v:
            vecs.append(v)
    if len(vecs) < 2:
        return None
    sims = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            sims.append(_cosine(vecs[i], vecs[j]))
    return 1.0 - (sum(sims) / len(sims))


class _FoldDone(Exception):
    # raise to force the fold's rollback; unambiguous even nested in tests
    pass


def _pick_user(name):
    # ponytail: single-user app; pass --user if the database ever grows one.
    User = get_user_model()
    return User.objects.get(username=name) if name else User.objects.first()


def run_eval(user, threshold=8.0, limit=20, kind="all", sample=0, verbose=False):
    """Leave-one-out over rated entries. Returns (summary, verbose_lines)."""
    features = _feature_map()
    folds, skipped = [], 0
    for leaf, entry_model in (("movie", UserMovie), ("show", UserShow)):
        if kind != "all" and kind != leaf:
            continue
        for entry in entry_model.objects.filter(
            user=user, rating__gte=threshold
        ).select_related(leaf):
            title = getattr(entry, leaf)
            if TITLE_KEY[leaf] + str(title.id) not in features:
                skipped += 1  # imported without usable genre priors
                continue
            folds.append((entry, leaf))
    if sample:
        random.shuffle(folds)
        folds = folds[:sample]

    total_catalog = Movie.objects.count() + Show.objects.count()
    hits = {k: 0 for k in HIT_KS}
    pop_hits = {k: 0 for k in HIT_KS}
    rr, hit_ranks = 0.0, []
    abs_errs, sq_errs, signed_errs, base_errs = [], [], [], []
    fallback, lines = 0, []
    recommended = set()
    diversities = []
    for (entry, leaf) in folds:
        title = getattr(entry, leaf)
        name = getattr(title, "title", None) or title.name
        tkey = TITLE_KEY[leaf] + str(title.id)
        actual = entry.rating
        try:
            with transaction.atomic():
                entry.delete()
                build_profile(user)
                recs = recommend_for_user(
                    user, kind=kind, limit=limit, jitter=False, skip_recent=False
                )
                for r in recs:
                    recommended.add((r["kind"], r["id"]))
                div = _list_diversity(recs, features)
                if div is not None:
                    diversities.append(div)
                rank = next(
                    (
                        r["rank"]
                        for r in recs
                        if r["kind"] == leaf and r["id"] == title.id
                    ),
                    None,
                )
                pop_rank = next(
                    (
                        i
                        for i, (c_leaf, c_title, _vec) in enumerate(
                            _candidates(user, kind, features), start=1
                        )
                        if c_leaf == leaf and c_title.id == title.id
                    ),
                    None,
                )
                pred, base, covered = predict_rating(user, tkey, features)
                raise _FoldDone
        except _FoldDone:
            pass
        if rank:
            for k in HIT_KS:
                if rank <= k:
                    hits[k] += 1
            rr += 1 / rank
            hit_ranks.append(rank)
        if pop_rank:
            for k in HIT_KS:
                if pop_rank <= k:
                    pop_hits[k] += 1
        if covered:
            abs_errs.append(abs(pred - actual))
            sq_errs.append((pred - actual) ** 2)
            signed_errs.append(pred - actual)
            base_errs.append(abs(base - actual))
        else:
            fallback += 1
        if verbose:
            shown = f"rank={rank}" if rank else "rank=-  MISS"
            lines.append(
                f"  {name}  actual={actual}  {shown}"
                f"  pred={pred:.2f}  err={pred - actual:+.2f}"
            )
    if not folds:
        return {"folds": 0, "skipped": skipped}, lines
    summary = {
        "algorithm_version": ALGORITHM_VERSION,
        "feature_version": FEATURE_VERSION,
        "folds": len(folds),
        "skipped": skipped,
        "fallback": fallback,
        "hits": hits,
        "pop_hits": pop_hits,
        "mrr": round(rr / len(folds), 4),
        "mean_hit_rank": (
            round(sum(hit_ranks) / len(hit_ranks), 2) if hit_ranks else None
        ),
        "mae": round(sum(abs_errs) / len(abs_errs), 4) if abs_errs else None,
        "rmse": round(math.sqrt(sum(sq_errs) / len(sq_errs)), 4) if sq_errs else None,
        "bias": round(sum(signed_errs) / len(signed_errs), 4) if signed_errs else None,
        "baseline_mae": round(sum(base_errs) / len(base_errs), 4) if base_errs else None,
        "diversity": (
            round(sum(diversities) / len(diversities), 4) if diversities else None
        ),
        "coverage": (
            round(len(recommended) / total_catalog, 4) if total_catalog else None
        ),
        "recommended": len(recommended),
        "catalog": total_catalog,
    }
    return summary, lines


class Command(BaseCommand):
    help = "Leave-one-out eval of the recommender: ranking + rating error."

    def add_arguments(self, parser):
        parser.add_argument("--threshold", type=float, default=8.0)
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--kind", choices=("all", "movie", "show"), default="all")
        parser.add_argument("--user", default="")
        parser.add_argument("--sample", type=int, default=0, help="random fold subset")
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args, **opts):
        user = _pick_user(opts["user"])
        summary, lines = run_eval(
            user,
            threshold=opts["threshold"],
            limit=opts["limit"],
            kind=opts["kind"],
            sample=opts["sample"],
            verbose=opts["verbose"],
        )
        out = self.stdout.write
        if not summary.get("folds"):
            out(f"No rated titles at or above threshold {opts['threshold']}.")
            return
        n = summary["folds"]
        out(
            f"{summary['algorithm_version']} "
            f"(features {summary['feature_version']})  user={user.username}"
        )
        out(
            f"folds={n}  skipped={summary['skipped']} unscorable  "
            f"rating-fallback={summary['fallback']}"
        )
        out("ranking (engine vs popularity baseline):")
        for k in HIT_KS:
            out(
                f"  hit@{k:<3} {summary['hits'][k] / n:.2f}"
                f"   baseline {summary['pop_hits'][k] / n:.2f}"
            )
        out(f"  MRR   {summary['mrr']:.2f}")
        if summary["mean_hit_rank"]:
            out(f"  mean rank of hits: {summary['mean_hit_rank']:.1f}")
        out(
            f"  intra-list diversity  {summary['diversity'] if summary['diversity'] is not None else 'n/a'}"
        )
        out(
            f"  coverage  {summary['coverage'] if summary['coverage'] is not None else 'n/a'} "
            f"({summary['recommended']}/{summary['catalog']} catalog)"
        )
        out("rating error (engine vs predict-the-average baseline):")
        out(f"  MAE   {summary['mae']:.2f}   baseline {summary['baseline_mae']:.2f}")
        out(f"  RMSE  {summary['rmse']:.2f}")
        out(f"  bias  {summary['bias']:+.2f}")
        for line in lines:
            out(line)
