const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p";

export type Genre = { id: number; tmdb_id: number; name: string };

export type Movie = {
  id: number;
  tmdb_id: number;
  title: string;
  original_title: string;
  release_date: string | null;
  release_year: number | null;
  runtime: number | null;
  overview: string;
  poster_path: string;
  backdrop_path: string;
  original_language: string;
  tagline: string;
  vote_average: number | null;
  vote_count: number | null;
  award_label: string;
  genres: Genre[];
};

export type Show = {
  id: number;
  tmdb_id: number;
  name: string;
  original_name: string;
  first_air_date: string | null;
  release_year: number | null;
  overview: string;
  original_language: string;
  poster_path: string;
  backdrop_path: string;
  seasons: number | null;
  episodes: number | null;
  is_anime: boolean;
  created_by: string;
  tagline: string;
  vote_average: number | null;
  vote_count: number | null;
  award_label: string;
  genres: Genre[];
};

export type LibraryStatus = "WATCHLIST" | "WATCHED" | "REJECTED" | "SKIPPED";

export type LibraryEntry = {
  id: number;
  movie: Movie;
  status: LibraryStatus;
  rating: number | null;
  personal_note: string;
  is_favorite: boolean;
  updated_at: string;
};

export type ShowEntry = {
  id: number;
  show: Show;
  status: LibraryStatus;
  rating: number | null;
  personal_note: string;
  is_favorite: boolean;
  updated_at: string;
};

export type TasteFeature = {
  feature: string;
  label: string;
  description: string;
  weight: number;
  evidence: number;
  strength: "strong" | "emerging";
  titles: { title: string; year: number | null; rating: number | null }[];
};

export type TasteProfile = {
  positive: TasteFeature[];
  negative: TasteFeature[];
  generated_at: string | null;
};

export type RecommendationReason = {
  feature: string;
  label: string;
  strength: number;
};

export type Recommendation = {
  kind: "movie" | "show";
  id: number;
  tmdb_id: number;
  title: string;
  year: number | null;
  release_date: string | null;
  poster_path: string;
  backdrop_path: string;
  overview: string;
  vote_average: number | null;
  vote_count: number | null;
  award_label: string | null;
  created_by: string | null;
  runtime: number | null;
  seasons: number | null;
  episodes: number | null;
  is_anime: boolean | null;
  original_language: string | null;
  genres: { id: number; name: string }[];
  score: number;
  rank: number;
  personalized: boolean;
  reasons: RecommendationReason[];
  similar_liked: { title: string; year: number | null; rating: number | null }[];
};

export type RecommendationsResponse = {
  results: Recommendation[];
  algorithm_version: string;
  feature_version: string;
  generated_at: string;
};

export type PairItem = {
  kind: "movie" | "show";
  id: number;
  tmdb_id: number;
  title: string;
  year: number | null;
  release_date: string | null;
  poster_path: string | null;
  overview: string;
  vote_average: number | null;
  genres: { id: number; name: string }[];
  tkey: string;
};

export type PairComparison = {
  id: number;
  tkey_a: string;
  tkey_b: string;
  winner_tkey: string;
  created_at: string | null;
};

export type FeedbackStats = {
  served: number;
  watched: number;
  rejected: number;
  conversion: number | null;
};

export type EntryPatch = {
  status?: LibraryStatus;
  is_favorite?: boolean;
  rating?: number | null;
  personal_note?: string;
};

export type SimilarItem = {
  local: boolean;
  kind: "movie" | "show";
  /** Local pk when local, otherwise the TMDB id (imported on click). */
  id: number;
  tmdb_id: number;
  title: string;
  year: number | null;
  poster_path: string | null;
};

export type TmdbTvResult = {
  id: number;
  name: string;
  first_air_date?: string;
  poster_path?: string | null;
  backdrop_path?: string | null;
  overview?: string;
  genre_ids?: number[];
  origin_country?: string[];
  vote_average?: number;
  vote_count?: number;
};

export type BrowseSection =
  | "trending"
  | "latest"
  | "upcoming"
  | "top_rated"
  | "awarded"
  | "genre";

export type MediaKind = "movie" | "show" | "anime";

export type TmdbVideo = {
  key: string;
  site: string;
  type: string;
  name: string;
  official?: boolean;
};

export type TmdbCastMember = {
  id: number;
  name: string;
  character?: string;
  profile_path?: string | null;
};

export type TmdbEpisode = {
  id: number;
  episode_number: number;
  name: string;
  overview: string;
  still_path?: string | null;
  runtime?: number | null;
  air_date?: string | null;
  vote_average?: number;
};

export type SearchResult = {
  id: number;
  title: string;
  release_date?: string;
  poster_path?: string | null;
  backdrop_path?: string | null;
  overview?: string;
  genre_ids?: number[];
  vote_average?: number;
  vote_count?: number;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${response.status}: ${detail.slice(0, 200)}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  movies: () => request<Movie[]>("/movies"),
  movie: (id: number) => request<Movie>(`/movies/${id}`),
  trending: () =>
    request<{ results: SearchResult[] }>("/movies/trending"),
  browse: (kind: MediaKind, section: BrowseSection, genre?: number, page = 1) =>
    request<{ results: (SearchResult & TmdbTvResult)[] }>(
      `/${kind === "movie" ? "movies" : kind === "show" ? "shows" : "anime"}/browse?section=${section}${genre ? `&genre=${genre}` : ""}&page=${page}`,
    ),
  genres: (media: "movie" | "tv") =>
    request<{ genres: { id: number; name: string }[] }>(
      `/genres?media=${media}`,
    ),
  searchMovies: (query: string) =>
    request<{ results: SearchResult[] }>(
      `/movies/search?q=${encodeURIComponent(query)}`,
    ),
  searchShows: (query: string) =>
    request<{ results: TmdbTvResult[] }>(
      `/shows/search?q=${encodeURIComponent(query)}`,
    ),
  importMovie: (tmdbId: number) =>
    request<Movie>("/movies/import", {
      method: "POST",
      body: JSON.stringify({ tmdb_id: tmdbId }),
    }),
  shows: () => request<Show[]>("/shows"),
  show: (id: number) => request<Show>(`/shows/${id}`),
  importShow: (tmdbId: number) =>
    request<Show>("/shows/import", {
      method: "POST",
      body: JSON.stringify({ tmdb_id: tmdbId }),
    }),
  library: () => request<LibraryEntry[]>("/library"),
  addToLibrary: (
    movieId: number,
    status: LibraryStatus,
    rating?: number | null,
  ) =>
    request<LibraryEntry>("/library", {
      method: "POST",
      body: JSON.stringify({
        movie_id: movieId,
        status,
        ...(rating != null ? { rating } : {}),
      }),
    }),
  updateEntry: (id: number, patch: EntryPatch) =>
    request<LibraryEntry>(`/library/items/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  deleteEntry: (id: number) =>
    request<void>(`/library/items/${id}`, { method: "DELETE" }),
  showsLibrary: () => request<ShowEntry[]>("/library/shows"),
  addShowToLibrary: (
    showId: number,
    status: LibraryStatus,
    rating?: number | null,
  ) =>
    request<ShowEntry>("/library/shows", {
      method: "POST",
      body: JSON.stringify({
        show_id: showId,
        status,
        ...(rating != null ? { rating } : {}),
      }),
    }),
  updateShowEntry: (id: number, patch: EntryPatch) =>
    request<ShowEntry>(`/library/shows/items/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  deleteShowEntry: (id: number) =>
    request<void>(`/library/shows/items/${id}`, { method: "DELETE" }),
  awardedMovies: () => request<Movie[]>("/movies/browse?section=awarded"),
  tasteProfile: () => request<TasteProfile>("/taste/profile"),
  recommendations: (kind: "all" | "movie" | "show" = "all", limit = 10, context?: string) =>
    request<RecommendationsResponse>(
      `/recommendations?kind=${kind}&limit=${limit}${context ? `&context=${context}` : ""}`,
    ),
  refreshRecommendations: () =>
    request<{ rebuilt_preferences: number }>("/recommendations/refresh", {
      method: "POST",
    }),
  recoFeedback: () => request<FeedbackStats>("/recommendations/feedback"),
  recoClick: (tkey: string, kind: string, titleId: number, position?: number) =>
    request<{ ok: boolean }>("/recommendations/click", {
      method: "POST",
      body: JSON.stringify({ tkey, kind, id: titleId, title_id: titleId, position }),
    }),
  tastePair: () =>
    request<{ a: PairItem; b: PairItem }>("/taste/pair"),
  tastePairSubmit: (tkeyA: string, tkeyB: string, winnerTkey: string) =>
    request<{ ok: boolean }>("/taste/pair/submit", {
      method: "POST",
      body: JSON.stringify({ tkey_a: tkeyA, tkey_b: tkeyB, winner_tkey: winnerTkey }),
    }),
  tastePairs: () => request<{ results: PairComparison[] }>("/taste/pairs"),
  titleVideos: (media: "movie" | "tv", tmdbId: number) =>
    request<{ results: TmdbVideo[] }>(`/tmdb/${media}/${tmdbId}/videos`),
  titleCredits: (media: "movie" | "tv", tmdbId: number) =>
    request<{ cast: TmdbCastMember[]; crew: { job?: string; name?: string }[] }>(
      `/tmdb/${media}/${tmdbId}/credits`,
    ),
  titleSimilar: (media: "movie" | "tv", tmdbId: number) =>
    request<{ results: (SearchResult & TmdbTvResult)[] }>(
      `/tmdb/${media}/${tmdbId}/similar`,
    ),
  titleSimilarLocal: (kind: "movie" | "show", id: number, limit = 12) =>
    request<{ results: SimilarItem[] }>(`/taste/similar/${kind}/${id}?limit=${limit}`),
  tvSeason: (tmdbId: number, season: number) =>
    request<{ season_number: number; episodes: TmdbEpisode[] }>(
      `/tmdb/tv/${tmdbId}/season/${season}`,
    ),
};

export function posterUrl(path: string | null | undefined, size = "w342") {
  return path ? `${TMDB_IMAGE_BASE}/${size}${path}` : null;
}

export function backdropUrl(path: string | null | undefined, size = "w1280") {
  return path ? `${TMDB_IMAGE_BASE}/${size}${path}` : null;
}
