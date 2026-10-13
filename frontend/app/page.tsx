"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, backdropUrl } from "@/lib/api";
import { Hero, type HeroSlide } from "@/components/Hero";
import { Row, type RailItem } from "@/components/Row";

const HALF_HOUR = 1000 * 60 * 30;

const GENRE_RAILS = [
  { id: 28, title: "Action", subtitle: "High impact" },
  { id: 18, title: "Drama", subtitle: "Stories that stay" },
  { id: 35, title: "Comedy", subtitle: "Lighten up" },
  { id: 53, title: "Thriller", subtitle: "Edge of seat" },
];

export default function Home() {
  const router = useRouter();
  const [pendingKey, setPendingKey] = useState<string | null>(null);

  const trendingMovies = useQuery({
    queryKey: ["trending"],
    queryFn: api.trending,
    staleTime: HALF_HOUR,
  });
  const trendingShows = useQuery({
    queryKey: ["browse", "show", "trending"],
    queryFn: () => api.browse("show", "trending"),
    staleTime: HALF_HOUR,
  });
  const topRated = useQuery({
    queryKey: ["browse", "movie", "top_rated"],
    queryFn: () => api.browse("movie", "top_rated"),
    staleTime: HALF_HOUR,
  });
  const awarded = useQuery({
    queryKey: ["awarded"],
    queryFn: api.awardedMovies,
    staleTime: HALF_HOUR,
  });
  const upcoming = useQuery({
    queryKey: ["browse", "movie", "upcoming"],
    queryFn: () => api.browse("movie", "upcoming"),
    staleTime: HALF_HOUR,
  });
  const genreRails = GENRE_RAILS.map((g) => ({
    // Fixed order — safe in a static map.
    query: useQuery({
      queryKey: ["browse", "movie", "genre", g.id],
      queryFn: () => api.browse("movie", "genre", g.id),
      staleTime: HALF_HOUR,
    }),
    ...g,
  }));

  const openResult = async (kind: "movie" | "show", tmdbId: number) => {
    setPendingKey(`${kind}-${tmdbId}`);
    try {
      if (kind === "movie") {
        const movie = await api.importMovie(tmdbId);
        router.push(`/movie/${movie.id}`);
      } else {
        const show = await api.importShow(tmdbId);
        router.push(`/show/${show.id}`);
      }
    } finally {
      setPendingKey(null);
    }
  };

  const slides: HeroSlide[] = [
    ...(trendingMovies.data?.results ?? [])
      .filter((r) => r.backdrop_path)
      .slice(0, 4)
      .map((r) => ({
        key: `tm-${r.id}`,
        title: r.title,
        meta: (r.release_date || "").slice(0, 4),
        overview: r.overview,
        backdrop: backdropUrl(r.backdrop_path),
        badge: "Trending movie",
        onOpen: () => openResult("movie", r.id),
        opening: pendingKey === `movie-${r.id}`,
      })),
    ...(trendingShows.data?.results ?? [])
      .filter((r) => r.backdrop_path)
      .slice(0, 3)
      .map((r) => ({
        key: `ts-${r.id}`,
        title: r.name,
        meta: (r.first_air_date || "").slice(0, 4),
        overview: r.overview,
        backdrop: backdropUrl(r.backdrop_path),
        badge: "Trending show",
        onOpen: () => openResult("show", r.id),
        opening: pendingKey === `show-${r.id}`,
      })),
  ];

  const railFor = (
    kind: "movie" | "show",
    r: { id: number; title?: string; name?: string; release_date?: string; first_air_date?: string; poster_path?: string | null },
  ): RailItem => ({
    key: `tmdb-${kind}-${r.id}`,
    title: (kind === "movie" ? r.title : r.name) ?? "Untitled",
    year: ((kind === "movie" ? r.release_date : r.first_air_date) || "").slice(0, 4) || undefined,
    posterPath: r.poster_path,
    onSelect: () => openResult(kind, r.id),
    selectPending: pendingKey === `${kind}-${r.id}`,
  });

  const loading = trendingMovies.isPending && trendingShows.isPending;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-6 py-8">
      {loading ? (
        <div className="neu-inset shimmer px-6 py-16" aria-busy>
          <p className="text-sm text-[#5b6b84]">Loading your cinema…</p>
        </div>
      ) : slides.length > 0 ? (
        <Hero slides={slides} />
      ) : (
        <div className="neu p-8">
          <h1 className="font-display text-2xl tracking-wide">WhatNext</h1>
          <p className="mt-2 max-w-lg text-sm text-[#5b6b84]">
            Trending picks will appear here once TMDB responds.
          </p>
        </div>
      )}

      <Row
        title="Top 10 movies today"
        subtitle="Ranked by the crowd"
        icon="trophy"
        numbered
        viewAllHref="/browse?media=movie&section=trending"
        items={(trendingMovies.data?.results ?? []).slice(0, 10).map((r) => railFor("movie", r))}
        empty="Top 10 unavailable."
      />
      <Row
        title="Top 10 shows today"
        subtitle="Series ranked by the crowd"
        icon="trophy"
        numbered
        viewAllHref="/browse?media=show&section=trending"
        items={(trendingShows.data?.results ?? []).slice(0, 10).map((r) => railFor("show", r))}
        empty="Top 10 shows unavailable."
      />
      <Row
        title="Top rated"
        subtitle="The highest verdicts of all time"
        icon="star"
        viewAllHref="/browse?media=movie&section=top_rated"
        items={(topRated.data?.results ?? []).slice(0, 12).map((r) => railFor("movie", r))}
        empty="Top rated unavailable."
      />
      {awarded.isError ? (
        <p className="text-sm text-[#5b6b84]">
          Award winners are being curated — check back soon.
        </p>
      ) : (
        <Row
          title="Award winners"
          subtitle="Oscars & Cannes selections"
          icon="trophy"
          viewAllHref="/browse?media=movie&section=awarded"
          items={(awarded.data ?? []).map((m) => ({
            key: `award-${m.id}`,
            title: m.title,
            year: m.release_year ? String(m.release_year) : undefined,
            tag: m.award_label || undefined,
            posterPath: m.poster_path,
            href: `/movie/${m.id}`,
          }))}
          empty="No award winners seeded yet."
        />
      )}
      <Row
        title="Coming soon"
        subtitle="Movies on the horizon"
        icon="calendar"
        viewAllHref="/browse?media=movie&section=upcoming"
        items={(upcoming.data?.results ?? []).slice(0, 12).map((r) => ({
          ...railFor("movie", r),
          year: (r.release_date || "").slice(0, 10) || undefined,
        }))}
        empty="Nothing upcoming found."
      />

      <header className="mt-2">
        <h2 className="font-display text-xl tracking-wide">Popular genres</h2>
        <p className="text-sm text-[#5b6b84]">A rail for every taste</p>
      </header>
      {genreRails.map(({ query, id, title, subtitle }) => (
        <Row
          key={id}
          title={title}
          subtitle={subtitle}
          icon="film"
          viewAllHref={`/browse?media=movie&section=genre&genre=${id}`}
          items={(query.data?.results ?? []).slice(0, 12).map((r) => railFor("movie", r))}
          empty=""
        />
      ))}
    </div>
  );
}
