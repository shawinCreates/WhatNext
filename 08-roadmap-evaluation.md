# Movie Brain --- Roadmap, Evaluation and Experiments

## 1. MVP

The MVP should support:

-   movie catalog
-   movie search
-   watched list
-   watchlist
-   ratings
-   reviews
-   explicit preference tags
-   basic taste profile
-   content-based recommendations
-   recommendation explanations

## 2. V1

Add: - embeddings - semantic candidate generation - multiple taste
clusters - negative preferences - diversity re-ranking - recommendation
feedback - pairwise comparisons

## 3. V2

Add: - learned ranking model - active learning - temporal taste
modeling - personalized exploration - recommendation experiments -
model/version tracking

## 4. Evaluation

Accuracy alone is not enough.

Measure:

### Rating prediction

-   MAE
-   RMSE
-   calibration

### Ranking

-   Precision@K
-   Recall@K
-   NDCG@K
-   Hit Rate@K

### Diversity

-   intra-list diversity
-   catalog coverage

### Discovery

-   percentage of recommendations that enter watchlist
-   percentage eventually watched

### User value

-   explicit recommendation satisfaction
-   rejection rate
-   "why recommended?" usefulness feedback

## 5. Offline evaluation

Use historical interactions.

Example:

``` text
Known history
    ↓
Hide one high-rated movie
    ↓
Generate recommendations
    ↓
Check whether hidden movie appears near the top
```

Use temporal splits rather than random splits when possible.

## 6. Online evaluation

Track:

``` text
recommendation shown
→ clicked
→ watchlisted
→ watched
→ rated
```

A recommendation that receives a click but never gets watched is
different from one that results in a high rating.

## 7. Cold start

For a new user: - ask a small set of preference questions - select
representative movie pairs - allow importing watched movies - use
explicit genres/themes temporarily

For this personal application, cold start is less important because the
user already has a substantial history.

## 8. Explainability evaluation

Every recommendation should answer:

1.  Why was it selected?
2.  Which user preferences contributed?
3.  Which liked movies support the recommendation?
4.  Is there an important mismatch?

## 9. Experiment tracking

Record:

``` text
algorithm_version
feature_version
embedding_model
candidate_source
weights
timestamp
```

This allows comparison between recommender versions.

## 10. Recommended development order

``` text
1. Supabase schema
2. Django models
3. Movie ingestion
4. Next.js library UI
5. Ratings/reviews
6. Feature taxonomy
7. LLM feature extraction
8. Taste profile
9. Embeddings
10. Candidate generation
11. Scoring
12. Diversity
13. Explanations
14. Feedback loop
15. Learning-to-rank
```

## 11. Long-term vision

The mature system should behave less like:

> "You liked movie X, so watch movie Y."

and more like:

> "Across your history, you repeatedly respond to psychological tension,
> ambitious characters, morally ambiguous situations, intellectually
> demanding narratives, and endings with strong narrative payoff. You
> tolerate slower pacing when the thematic or character payoff is
> strong. This recommendation matches those traits while introducing a
> different setting and genre."

That is the target behavior of Movie Brain.
