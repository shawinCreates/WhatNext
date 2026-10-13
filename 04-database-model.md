# Movie Brain --- Database Model

## 1. Database

Primary database: Supabase PostgreSQL.

Use `pgvector` for semantic embeddings.

Django ORM should own application-level database access.

## 2. Core tables

### movies

``` text
id
tmdb_id
imdb_id
title
original_title
release_date
release_year
runtime
overview
original_language
poster_path
backdrop_path
created_at
updated_at
```

### genres

``` text
id
name
```

### movie_genres

``` text
movie_id
genre_id
```

### people

``` text
id
external_id
name
```

### movie_people

``` text
movie_id
person_id
role
character_name
```

## 3. Movie intelligence

### movie_features

``` text
id
movie_id
feature_key
value
confidence
source
```

Example:

``` text
movie_id: 123
feature_key: moral_ambiguity
value: 0.91
confidence: 0.84
source: llm
```

### movie_embeddings

``` text
id
movie_id
embedding
model_name
content_hash
created_at
```

Use a vector column through pgvector.

## 4. User library

### user_movies

``` text
id
user_id
movie_id
status
rating
watched_at
rewatched_count
personal_note
created_at
updated_at
```

Status examples:

``` text
WATCHED
WATCHLIST
REJECTED
SKIPPED
```

## 5. Feedback

### movie_reviews

``` text
id
user_movie_id
review_text
created_at
updated_at
```

### feedback_tags

``` text
id
user_movie_id
feature_key
polarity
strength
source
confidence
```

### movie_comparisons

``` text
id
user_id
movie_a_id
movie_b_id
preferred_movie_id
reason
created_at
```

Pairwise comparisons are valuable for learning relative preference.

## 6. User taste

### user_preferences

``` text
id
user_id
feature_key
polarity
weight
confidence
source
updated_at
```

### taste_clusters

``` text
id
user_id
name
description
weight
embedding
```

### taste_cluster_movies

``` text
cluster_id
movie_id
association_score
```

## 7. Recommendations

### recommendations

``` text
id
user_id
movie_id
score
rank
algorithm_version
generated_at
```

### recommendation_reasons

``` text
id
recommendation_id
feature_key
contribution
explanation
```

### recommendation_feedback

``` text
id
recommendation_id
action
created_at
```

Actions: - clicked - watchlisted - rejected - watched - rated

## 8. Important constraints

-   One user/movie library record per user.
-   External movie IDs should be indexed and unique where possible.
-   Feature keys should be normalized.
-   Recommendation records should retain algorithm version.
-   Embeddings must record model name and content hash so they can be
    regenerated safely.

## 9. Indexing

Recommended indexes: - `movies.tmdb_id` - `movies.imdb_id` -
`movies.title` - `user_movies(user_id, status)` -
`user_movies(user_id, movie_id)` -
`user_preferences(user_id, feature_key)` - vector index on embeddings
when dataset size makes it useful.
