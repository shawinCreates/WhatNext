# Movie Brain --- API and Frontend Design

## 1. API style

Django REST Framework.

Base path:

``` text
/api/v1/
```

## 2. Movie endpoints

``` text
GET    /movies
GET    /movies/{id}
GET    /movies/search?q=
POST   /movies/import
```

## 3. Library endpoints

``` text
GET    /library
POST   /library/movies
PATCH  /library/movies/{id}
DELETE /library/movies/{id}
```

## 4. Feedback endpoints

``` text
POST /movies/{id}/rating
POST /movies/{id}/review
POST /movies/{id}/feedback
POST /comparisons
```

## 5. Taste endpoints

``` text
GET  /taste/profile
GET  /taste/clusters
GET  /taste/preferences
POST /taste/preferences
```

## 6. Recommendation endpoints

``` text
GET  /recommendations
GET  /recommendations/{id}
POST /recommendations/{id}/feedback
POST /recommendations/refresh
```

## 7. Recommendation response

Example:

``` json
{
  "movie": {
    "id": 123,
    "title": "Zodiac",
    "year": 2007
  },
  "score": 0.91,
  "rank": 1,
  "reasons": [
    {
      "feature": "psychological_tension",
      "strength": 0.94
    },
    {
      "feature": "narrative_complexity",
      "strength": 0.89
    }
  ],
  "similar_liked_movies": [
    "Se7en",
    "Prisoners",
    "The Prestige"
  ]
}
```

## 8. Next.js application structure

``` text
app/
├── page.tsx
├── discover/
├── movies/
│   └── [id]/
├── library/
├── watchlist/
├── taste/
│   ├── profile/
│   └── clusters/
└── settings/
```

Components:

``` text
components/
├── movie-card/
├── movie-grid/
├── rating-input/
├── taste-profile/
├── taste-cluster/
├── recommendation-card/
├── recommendation-reason/
└── comparison-picker/
```

## 9. Main screens

### Dashboard

Shows: - recently watched - current watchlist - top recommendations -
taste changes - recent feedback

### Movie detail

Shows: - metadata - poster - themes - user's rating - notes -
recommendation relevance

### Discover

Shows: - personalized recommendations - filters - exploration modes -
recommendation explanations

### Taste profile

Shows: - strongest positive preferences - negative preferences - taste
clusters - recent changes

### Comparison mode

Two movie cards:

``` text
Which would you rather watch?

[ Movie A ]       [ Movie B ]
```

This is both a useful UI and valuable training data.

## 10. UX principle

Do not overwhelm the user with machine-learning terminology.

Show:

> You tend to enjoy complex stories with psychological tension.

Instead of:

> latent embedding cluster #4 has cosine similarity 0.87.
