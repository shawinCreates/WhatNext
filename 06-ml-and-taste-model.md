# Movie Brain --- ML, Taste Modeling and Learning

## 1. Modeling philosophy

Start with interpretable hybrid recommendation rather than deep
learning.

The user initially has a small personal dataset, so a large neural
recommender would overfit.

## 2. Taste vector

A simplified user taste vector can be calculated as a weighted aggregate
of movie feature vectors.

For watched movie i:

``` text
movie_vector_i
```

With user preference weight:

``` text
interaction_weight_i
```

A simple profile is:

``` text
user_vector =
    weighted_mean(movie_vectors)
```

Weights can depend on: - rating - recency - rewatch behavior - explicit
positive/negative feedback

## 3. Rating-based weighting

Example:

``` text
rating >= 9  → strong positive
rating 7-8   → moderate positive
rating 5-6   → neutral/mixed
rating <= 4  → negative
```

The exact mapping should remain configurable.

## 4. Recency

Taste can evolve.

Use time decay:

``` text
weight = exp(-lambda * age_in_days)
```

Do not make recency dominate by default. Long-term preferences should
remain stable unless new evidence is strong.

## 5. Preference extraction with an LLM

Input:

``` text
User review:
"I loved the obsession between the two characters,
the confusing structure, and how everything clicked
at the end."
```

Output:

``` json
{
  "positive": {
    "obsession": 0.9,
    "narrative_complexity": 0.85,
    "payoff": 0.95
  }
}
```

Store the extracted result and source text.

Never silently overwrite the user's original review.

## 6. Embeddings

Create embeddings for: - movie descriptions - movie theme summaries -
user taste summaries - taste clusters

Store model name and version.

## 7. Supervised learning

Once enough interaction data exists, create training examples:

``` text
movie features → user's observed preference
```

Possible models: - logistic regression - random forest - XGBoost -
LightGBM

Predict:

``` text
P(user rates movie >= threshold)
```

or directly learn a ranking function.

## 8. Pairwise preference learning

Comparisons are highly valuable:

``` text
User prefers A over B
```

Training data becomes:

``` text
(A_features, B_features) → A wins
```

This can support pairwise ranking models.

## 9. Taste clusters

Cluster high-rated movies using: - feature vectors - embeddings -
interaction weights

Possible methods: - K-Means - HDBSCAN - hierarchical clustering

Cluster labels should be generated or refined with human-readable
summaries.

## 10. Active learning

When the model is uncertain, ask targeted questions.

Example:

> Which would you rather watch? A: Zodiac B: A Separation

This can identify a latent preference more efficiently than random
ratings.

## 11. Avoid overfitting

Do not infer a strong preference from one movie.

Require: - repeated evidence - confidence estimates - explicit
confirmation for important preferences

Separate:

``` text
observed behavior
```

from:

``` text
inferred preference
```
