# Movie Brain --- System Architecture

## 1. High-level architecture

``` text
                    ┌─────────────────────┐
                    │      Next.js        │
                    │     Web Client      │
                    └──────────┬──────────┘
                               │ HTTPS / JSON
                               ▼
                    ┌─────────────────────┐
                    │ Django + DRF API    │
                    │                     │
                    │ Auth / Library      │
                    │ Movies / Taste      │
                    │ Recommendations     │
                    └───────┬─────┬───────┘
                            │     │
                 ┌──────────┘     └──────────────┐
                 ▼                               ▼
        ┌─────────────────┐             ┌──────────────────┐
        │ Supabase        │             │ AI / ML Layer    │
        │ PostgreSQL      │             │                  │
        │ + pgvector      │             │ embeddings       │
        │                 │             │ LLM extraction   │
        │ core data       │             │ ranking models   │
        └─────────────────┘             └──────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ External Movie  │
        │ Metadata Source │
        └─────────────────┘
```

## 2. Responsibility boundaries

### Next.js

Responsible for: - UI - routing - server/client rendering - user
interactions - recommendation presentation - filtering and browsing -
optimistic UI where appropriate

It should not contain recommendation logic.

### Django

Responsible for: - business logic - authorization - API contracts -
database access - recommendation orchestration - validation - background
task coordination

### Supabase

Responsible for: - PostgreSQL - pgvector - optional file storage -
database backups and platform operations

Django remains the application's primary business-logic layer.

### AI/ML layer

Responsible for: - embeddings - extracting semantic attributes -
taste-profile generation - ranking - recommendation explanations

## 3. Request flow

``` text
User opens Discover
        ↓
Next.js requests /api/recommendations
        ↓
Django authenticates user
        ↓
Recommendation service loads:
  - watched history
  - explicit preferences
  - taste vectors
  - candidate movies
        ↓
Candidate generation
        ↓
Scoring
        ↓
Diversity re-ranking
        ↓
Explanation generation
        ↓
JSON response
        ↓
Next.js renders recommendation cards
```

## 4. Background processing

Expensive operations should not block normal requests.

Examples: - Movie metadata ingestion - Embedding generation - LLM
feature extraction - Taste profile recomputation - Large-scale
recommendation generation - Model training

Use a Django-compatible task system when the workload requires it.

## 5. Architectural principle

Keep recommendation algorithms behind a service interface:

``` python
RecommendationService.recommend(user, context)
```

This allows the internal algorithm to evolve without changing the API or
frontend.
