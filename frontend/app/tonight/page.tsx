"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  api,
  backdropUrl,
  type SearchResult,
  type TmdbTvResult,
} from "@/lib/api";
import { QuickSearch, useReveal } from "@/components/QuickSearch";
import { TonightPick, type TonightPick as Pick } from "@/components/TonightPick";
import { Row, type RailItem } from "@/components/Row";
import { Icon } from "@/components/icons";

const HALF_HOUR = 1000 * 60 * 30;

type TmdbItem = SearchResult & TmdbTvResult;

function titleOf(item: TmdbItem) {
  return item.title || item.name || "Untitled";
}

function yearOf(item: TmdbItem, kind: "movie" | "show") {
  return ((kind === "movie" ? item.release_date : item.first_air_date) || "").slice(0, 4) || undefined;
}

const MOODS = [
  { label: "Action", icon: "flame" as const, href: "/movies?genre=28" },
  { label: "Laugh", icon: "sparkles" as const, href: "/movies?genre=35" },
  { label: "Drama", icon: "film" as const, href: "/shows?genre=18" },
  { label: "Sci-Fi", icon: "compass" as const, href: "/shows?genre=10765" },
  { label: "Anime", icon: "star" as const, href: "/anime" },
];

export default function TonightPage() {
  const [term, setTerm] = useState("");
  const [debounced, setDebounced] = useState("");
  const { open, pendingKey } = useReveal();

  const topMovies = useQuery({
    queryKey: ["browse", "movie", "top_rated"],
    queryFn: () => api.browse("movie", "top_rated"),
    staleTime: HALF_HOUR,
  });
  const topShows = useQuery({
    queryKey: ["browse", "show", "top_rated"],
    queryFn: () => api.browse("show", "top_rated"),
    staleTime: HALF_HOUR,
  });
  const weekShows = useQuery({
    queryKey: ["browse", "show", "latest"],
    queryFn: () => api.browse("show", "latest"),
    staleTime: HALF_HOUR,
  });
  const weekAnime = useQuery({
    queryKey: ["browse", "anime", "latest"],
    queryFn: () => api.browse("anime", "latest"),
    staleTime: HALF_HOUR,
  });

  const toRail = (kind: "movie" | "show", item: TmdbItem): RailItem => ({
    key: `${kind}-${item.id}`,
    title: titleOf(item),
    year: yearOf(item, kind),
    posterPath: item.poster_path,
    onSelect: () => open(kind, item.id),
    selectPending: pendingKey === `open-${kind}-${item.id}`,
  });

  const voteOf = (item: TmdbItem) =>
    typeof item.vote_average === "number" ? ` · ★ ${item.vote_average.toFixed(1)}` : "";

  const picks: Pick[] = [
    ...(topMovies.data?.results ?? []).slice(0, 3).map((item) => ({ kind: "movie" as const, item })),
    ...(topShows.data?.results ?? []).slice(0, 3).map((item) => ({ kind: "show" as const, item })),
  ]
    .filter(({ item }) => item.backdrop_path)
    .slice(0, 5)
    .map(({ kind, item }) => ({
      key: `${kind}-${item.id}`,
      title: titleOf(item),
      meta: [yearOf(item, kind), kind === "movie" ? "Movie" : "Series"].filter(Boolean).join("  •  "),
      overview: item.overview,
      backdrop: backdropUrl(item.backdrop_path),
      badge: "Tonight's pick",
      reason: `Top rated with the crowd${voteOf(item)} — shuffle for another.`,
      onOpen: () => open(kind, item.id),
      opening: pendingKey === `open-${kind}-${item.id}`,
    }));

  const ratedItems = [
    ...(topMovies.data?.results ?? []).slice(0, 6).map((item) => ({ kind: "movie" as const, item })),
    ...(topShows.data?.results ?? []).slice(0, 6).map((item) => ({ kind: "show" as const, item })),
  ]
    .slice(0, 12)
    .map(({ kind, item }) => toRail(kind, item));

  const weekItems = [
    ...(weekShows.data?.results ?? []).slice(0, 6).map((item) => ({ kind: "show" as const, item })),
    ...(weekAnime.data?.results ?? []).slice(0, 6).map((item) => ({ kind: "show" as const, item })),
  ]
    .slice(0, 12)
    .map(({ kind, item }) => toRail(kind, item));

  const loading = topMovies.isPending && topShows.isPending;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-6 py-8">
      <section className="neu p-6 sm:p-8" aria-label="What to watch">
        <h1 className="font-display text-xl tracking-wide sm:text-2xl">
          What are you in the mood for?
        </h1>
        <div className="relative mt-4">
          <div className="neu-inset flex items-center gap-3 px-5 py-3.5">
            <Icon name="search" size={18} />
            <input
              value={term}
              onChange={(e) => {
                setTerm(e.target.value);
                setDebounced(e.target.value.trim());
              }}
              placeholder="A title, a show, an anime…"
              aria-label="Search titles"
              className="w-full bg-transparent text-base outline-none placeholder:text-[#8a99b0]"
            />
            {term && (
              <button
                type="button"
                onClick={() => {
                  setTerm("");
                  setDebounced("");
                }}
                aria-label="Clear search"
              >
                <Icon name="x" size={16} />
              </button>
            )}
          </div>
          <QuickSearch query={debounced} />
        </div>
        <div className="no-scrollbar mt-4 flex gap-2.5 overflow-x-auto pb-1">
          {MOODS.map((m) => (
            <Link
              key={m.label}
              href={m.href}
              className="neu flex flex-shrink-0 items-center gap-2 px-4 py-2 text-sm font-medium"
            >
              <Icon name={m.icon} size={15} />
              {m.label}
            </Link>
          ))}
        </div>
      </section>

      {loading ? (
        <div className="neu-inset shimmer px-6 py-16" aria-busy>
          <p className="text-sm text-[#5b6b84]">Picking tonight's titles…</p>
        </div>
      ) : picks.length > 0 ? (
        <TonightPick picks={picks} />
      ) : (
        <div className="neu p-8">
          <h2 className="font-display text-xl tracking-wide">Start with one title</h2>
          <p className="mt-2 max-w-lg text-sm text-[#5b6b84]">
            Search above or pick a mood — tonight's picks appear once the crowd data loads.
          </p>
        </div>
      )}

      <Row
        title="Top rated tonight"
        subtitle="The crowd's highest verdicts"
        icon="trophy"
        viewAllHref="/browse?media=movie&section=top_rated"
        items={ratedItems}
        empty="Nothing rated yet — check the hubs."
      />

      <Row
        title="On this week"
        subtitle="Airing now across shows and anime"
        icon="calendar"
        viewAllHref="/browse?media=show&section=latest"
        items={weekItems}
        empty="Airing data unavailable."
      />

      <footer className="flex justify-center pb-4">
        <p className="font-mono text-xs text-[#5b6b84]">
          WhatNext · movies, shows & anime
        </p>
      </footer>
    </div>
  );
}
