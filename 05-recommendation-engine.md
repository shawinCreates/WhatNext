# Movie Brain --- Recommendation Engine

## 1. Objective

Estimate how well an unseen movie fits the user's current taste while
maintaining novelty, diversity, and explainability.

The system should not reduce taste to genre similarity.

## 2. Pipeline

``` text
Movie catalog
    ↓
Candidate generation
    ↓
Hard filtering
    ↓
Feature extraction
    ↓
Taste matching
    ↓
Hybrid scoring
    ↓
Diversity re-ranking
    ↓
Explanation generation
    ↓
Top recommendations
```

## 3. Candidate generation

Use several sources:

### Semantic candidates

Nearest movies in embedding space.

### Taste-feature candidates

Movies matching highly weighted user preferences.

### Entity candidates

Movies connected to favored directors, actors, writers, or franchises.

### Discovery candidates

Critically notable or underexposed movies that fit broad preferences.

The final candidate pool can combine these sources.

## 4. Hard filtering

Remove: - watched movies - rejected movies - duplicate editions -
unavailable records - movies explicitly excluded by the user

## 5. Initial scoring

A practical v1 formula:

``` text
score =
    0.30 * semantic_similarity
  + 0.25 * taste_feature_match
  + 0.15 * predicted_rating
  + 0.10 * narrative_match
  + 0.05 * entity_affinity
  + 0.10 * novelty
  + 0.05 * quality_signal
```

These weights are starting values, not permanent truths.

## 6. Negative preferences

Negative signals should subtract from the score.

For example:

``` text
final_score =
positive_score - negative_penalty
```

A strong negative preference should have more influence than a weak
positive similarity.

## 7. Context-aware taste

The user may have different tastes in different contexts.

Possible contexts: - tonight - weekend - serious drama - short movie -
sci-fi - historical - "something surprising"

Context should modify candidate ranking without replacing the long-term
profile.

## 8. Diversity

Avoid returning ten nearly identical movies.

Use a diversity-aware re-ranking method such as Maximal Marginal
Relevance.

Conceptually:

``` text
MMR =
    relevance(candidate)
    - lambda * similarity(candidate, already_selected)
```

## 9. Explanations

Each recommendation should expose its strongest evidence.

Example:

``` text
Why this movie?

+ High psychological depth
+ Complex narrative
+ Moral ambiguity
+ Strong character conflict

Similar high-rated movies:
- Se7en
- Prisoners
- The Prestige
```

Do not expose arbitrary model internals as facts.

## 10. Algorithm versions

Every recommendation should record:

``` text
algorithm_version
feature_version
embedding_model
generated_at
```

This makes experiments reproducible.
