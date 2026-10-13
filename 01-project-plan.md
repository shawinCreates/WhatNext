# Movie Brain --- Project Plan

## 1. Vision

Movie Brain is a personal movie-management and recommendation
application designed to learn a user's nuanced movie taste rather than
relying only on genres, ratings, or simple "similar movie" matching.

The system should answer:

> Why does this user like particular movies, under what circumstances,
> and which unseen movies are most likely to fit that taste?

## 2. Goals

-   Maintain a structured personal movie library.
-   Track watched, watchlist, skipped, rejected, and rewatched movies.
-   Capture ratings, reactions, reviews, and reasons for
    liking/disliking a movie.
-   Model explicit and implicit preferences.
-   Represent movies through metadata, themes, narrative
    characteristics, tone, and semantic embeddings.
-   Generate explainable recommendations.
-   Learn continuously from new feedback.
-   Support multiple taste clusters rather than assuming one-dimensional
    taste.
-   Provide discovery and exploration, not only safe recommendations.

## 3. Non-goals for the first release

-   Building a public social network.
-   Competing with large commercial recommendation platforms.
-   Training a large foundation model.
-   Building a complete streaming service.
-   Perfectly predicting ratings.

## 4. Target stack

### Frontend

-   Next.js
-   TypeScript
-   Tailwind CSS
-   React Query or equivalent server-state layer

### Backend

-   Django
-   Django REST Framework
-   Django ORM
-   Django management commands / background jobs

### Platform

-   Supabase PostgreSQL
-   Supabase Storage where useful
-   Supabase authentication only if it simplifies the chosen auth
    architecture

### ML / AI

-   Python
-   scikit-learn
-   XGBoost or LightGBM later
-   Embedding model
-   LLM for semantic preference extraction and explanations

## 5. Development phases

### Phase 1 --- Foundation

-   Repository setup
-   Django project
-   Next.js application
-   Supabase project
-   Environment configuration
-   CI/CD
-   Base database schema

### Phase 2 --- Movie library

-   Movie ingestion
-   Movie search
-   Movie detail page
-   Watched/watchlist management
-   Ratings and notes

### Phase 3 --- Taste model

-   Preference taxonomy
-   Preference extraction
-   Movie feature vectors
-   Initial user taste profile
-   Taste dashboard

### Phase 4 --- Recommendation engine

-   Candidate generation
-   Content similarity
-   Taste-profile scoring
-   Hybrid scoring
-   Diversity-aware re-ranking
-   Explainable recommendations

### Phase 5 --- Learning loop

-   Recommendation impressions
-   Accept/reject feedback
-   Pairwise comparisons
-   Rating prediction
-   Weight learning

### Phase 6 --- Advanced intelligence

-   Taste clusters
-   Active learning
-   Learning-to-rank
-   Temporal taste modeling
-   Recommendation experiments

## 6. Definition of success

A successful v1 should: 1. Correctly represent the user's watched
history. 2. Explain recommendations using recognizable taste signals. 3.
Avoid repeatedly recommending already-watched or rejected titles. 4.
Produce diverse recommendations. 5. Improve as the user provides
feedback.
