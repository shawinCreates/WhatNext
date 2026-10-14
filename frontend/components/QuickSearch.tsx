"use client";

import { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, posterUrl } from "@/lib/api";
import { go } from "@/lib/motion";
import { Icon } from "@/components/icons";

/** Shared import-and-reveal action: open a TMDB id on its detail page. */
export function useReveal() {
  const router = useRouter();
  const [pendingKey, setPendingKey] = useState<string | null>(null);

  const open = async (kind: "movie" | "show", tmdbId: number) => {
    setPendingKey(`open-${kind}-${tmdbId}`);
    try {
      if (kind === "movie") {
        const movie = await api.importMovie(tmdbId);
        go(router, `/movie/${movie.id}`);
      } else {
        const show = await api.importShow(tmdbId);
        go(router, `/show/${show.id}`);
      }
    } finally {
      setPendingKey(null);
    }
  };

  return { open, pendingKey };
}

export type QuickResult = {
  key: string;
  kind: "movie" | "show";
  tmdbId: number;
  title: string;
  year: string;
  poster: string | null;
};

/** Shared TMDB quick-search dropdown: movies + shows, tap to import + open. */
export function QuickSearch({ query }: { query: string }) {
  const router = useRouter();
  const [pending, setPending] = useState<string | null>(null);
  const active = query.length > 1;

  const movieSearch = useQuery({
    queryKey: ["quick-search-movie", query],
    queryFn: () => api.searchMovies(query),
    enabled: active,
    staleTime: 1000 * 60 * 5,
  });
  const showSearch = useQuery({
    queryKey: ["quick-search-show", query],
    queryFn: () => api.searchShows(query),
    enabled: active,
    staleTime: 1000 * 60 * 5,
  });

  const openResult = useMutation({
    mutationFn: async ({ kind, tmdbId }: { kind: "movie" | "show"; tmdbId: number }) => {
      setPending(`${kind}-${tmdbId}`);
      try {
        if (kind === "movie") {
          const movie = await api.importMovie(tmdbId);
          return `/movie/${movie.id}`;
        }
        const show = await api.importShow(tmdbId);
        return `/show/${show.id}`;
      } finally {
        setPending(null);
      }
    },
    onSuccess: (href) => {
      go(router, href);
    },
  });

  if (!active) return null;

  const results: QuickResult[] = [
    ...(movieSearch.data?.results ?? []).slice(0, 4).map((r) => ({
      key: `m-${r.id}`,
      kind: "movie" as const,
      tmdbId: r.id,
      title: r.title,
      year: (r.release_date || "").slice(0, 4),
      poster: posterUrl(r.poster_path, "w92"),
    })),
    ...(showSearch.data?.results ?? []).slice(0, 4).map((r) => ({
      key: `s-${r.id}`,
      kind: "show" as const,
      tmdbId: r.id,
      title: r.name,
      year: (r.first_air_date || "").slice(0, 4),
      poster: posterUrl(r.poster_path, "w92"),
    })),
  ];

  const searching = movieSearch.isFetching || showSearch.isFetching;

  return (
    <div className="neu absolute top-full right-0 left-0 z-50 mt-3 p-2">
      {searching && <p className="px-3 py-4 text-sm text-[#5b6b84]">Searching…</p>}
      {!searching && results.length === 0 && (
        <p className="px-3 py-4 text-sm text-[#5b6b84]">No matches for “{query}”.</p>
      )}
      <ul className="max-h-80 overflow-y-auto">
        {results.map((r) => (
          <li key={r.key}>
            <button
              type="button"
              disabled={openResult.isPending}
              onClick={() => openResult.mutate({ kind: r.kind, tmdbId: r.tmdbId })}
              className="flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left hover:bg-white/50 disabled:opacity-60"
            >
              {r.poster ? (
                <Image
                  src={r.poster}
                  alt=""
                  width={34}
                  height={51}
                  className="flex-shrink-0 rounded object-cover"
                />
              ) : (
                <span className="neu-inset flex h-[51px] w-[34px] flex-shrink-0 items-center justify-center rounded">
                  <Icon name={r.kind === "movie" ? "film" : "tv"} size={14} />
                </span>
              )}
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{r.title}</span>
                <span className="text-xs text-[#5b6b84]">
                  {r.kind === "movie" ? "Movie" : "Show"} {r.year && `• ${r.year}`}
                </span>
              </span>
              {pending === `${r.kind}-${r.tmdbId}` && (
                <span className="text-xs text-[#5b6b84]">Opening…</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
