# Movie Brain --- Domain Concepts

## 1. Movie

A canonical film entity identified by external IDs where available.

Examples: - title - release year - runtime - genres - people -
overview - themes - tone - narrative characteristics

## 2. Movie DNA

Movie DNA is a structured representation of characteristics that can
influence user enjoyment.

Example:

``` json
{
  "psychological_depth": 0.92,
  "narrative_complexity": 0.88,
  "moral_ambiguity": 0.84,
  "character_complexity": 0.91,
  "emotional_intensity": 0.73,
  "slow_burn": 0.68,
  "philosophical_depth": 0.80,
  "visual_style": 0.77
}
```

These values are not objective truths. They are modeling features used
for recommendation.

## 3. User interaction

An interaction records what the user did with a movie.

Possible states: - discovered - watchlisted - watched - rewatched -
rejected - skipped

Additional feedback: - rating - review - reaction - tags - reasons -
comparison

## 4. Explicit preference

A preference directly stated by the user.

Example:

> I like morally ambiguous characters.

Represent it as:

``` text
feature = moral_ambiguity
polarity = positive
strength = 0.9
confidence = 0.95
```

## 5. Implicit preference

A preference inferred from behavior.

Example: - user repeatedly rates complex thrillers highly - user rejects
shallow action films

The system can infer a positive association with narrative complexity.

## 6. Taste dimension

A reusable semantic axis.

Examples: - intellectual depth - emotional intensity - character
complexity - ambiguity - atmosphere - pacing - narrative complexity -
philosophical depth - realism - historical context - visual style

## 7. Taste cluster

A coherent subset of the user's preferences.

A user might have:

``` text
Psychological thrillers
Philosophical dramas
Historical human stories
Ambition/obsession narratives
Science fiction with philosophical themes
```

One movie can belong to several clusters.

## 8. Candidate

A movie eligible for recommendation before final ranking.

## 9. Recommendation

A candidate that has passed scoring, filtering, and diversity rules.

A recommendation should store its generation context so it can later be
evaluated.

## 10. Recommendation explanation

A concise explanation connecting the movie to observed preferences.

Example:

> Recommended because you consistently respond well to psychological
> tension, complex narratives, moral ambiguity, and strong endings.

The explanation must reflect actual stored signals rather than inventing
reasons.
