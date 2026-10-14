"use client";

import { Suspense, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  api,
  posterUrl,
  type BrowseSection,
  type MediaKind,
  type SearchResult,
  type TmdbTvResult,
} from "@/lib/api";
import { go } from "@/lib/motion";
import { Icon } from "@/components/icons";

const TITLES: Record<string, { heading: string; sub: string }> = {
  "movie:trending": { heading: "Trending movies", sub: "What everyone is watching" },
  "movie:latest": { heading: "Latest movies", sub: "Now playing" },
  "movie:upcoming": { heading: "Upcoming movies", sub: "On the horizon" },
  "movie:top_rated": { heading: "Top rated movies", sub: "Highest verdicts of all time" },
  "movie:awarded": { heading: "Award winners", sub: "Oscars & Cannes selections" },
  "show:trending": { heading: "Trending shows", sub: "Series everyone is watching" },
  "show:latest": { heading: "Latest shows", sub: "Airing now" },
  "show:upcoming": { heading: "Upcoming shows", sub: "Premieres ahead" },
  "show:top_rated": { heading: "Top rated shows", sub: "Highest verdicts of all time" },
  "show:awarded": { heading: "Acclaimed shows", sub: "Decorated series" },
  "anime:trending": { heading: "Trending anime", sub: "Japanese animation now" },
  "anime:latest": { heading: "Latest anime", sub: "Fresh simulcasts" },
  "anime:upcoming": { heading: "Upcoming anime", sub: "Next season" },
  "anime:top_rated": { heading: "Top rated anime", sub: "All-time greats" },
  "anime:awarded": { heading: "Acclaimed anime", sub: "Decorated animation" },
};

function titleFor(kind: MediaKind, section: BrowseSection, genreName: string | null) {
  if (section === "genre")
    return {
      heading: genreName ? `${genreName} ${kind === "movie" ? "movies" : kind === "show" ? "shows" : "anime"}` : "Genre",
      sub: "Browse the shelf",
    };
  return (
    TITLES[`${kind}:${section}`] ?? { heading: "Browse", sub: "The full shelf" }
  );
}

function BrowseGrid() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const rawMedia = searchParams.get("media");
  const rawSection = searchParams.get("section");
  const kind: MediaKind = rawMedia === "show" || rawMedia === "anime" ? rawMedia : "movie";
  const section: BrowseSection =
    rawSection === "latest" ||
    rawSection === "upcoming" ||
    rawSection === "top_rated" ||
    rawSection === "awarded" ||
    rawSection === "genre"
      ? rawSection
      : "trending";
  const genre = Number(searchParams.get("genre")) || undefined;
  const [items, setItems] = useState<(SearchResult & TmdbTvResult)[]>([]);
  const [loadedPage, setLoadedPage] = useState(1);
  const [exhausted, setExhausted] = useState(false);
  const [appending, setAppending] = useState(false);
  const [appendError, setAppendError] = useState<string | null>(null);
  const [pending, setPending] = useState<number | null>(null);

  const genreName = useQuery({
    queryKey: ["genres", kind],
    queryFn: () => api.genres(kind === "movie" ? "movie" : "tv"),
    enabled: section === "genre",
    staleTime: 1000 * 60 * 60,
  });

  const first = useQuery({
    queryKey: ["browse-all", kind, section, genre],
    queryFn: () => api.browse(kind, section, genre, 1),
    staleTime: 1000 * 60 * 30,
  });

  // New shelf → seed from page one.
  useEffect(() => {
    if (first.data) {
      setItems(first.data.results);
      setLoadedPage(1);
      setExhausted(first.data.results.length === 0);
      setAppendError(null);
    }
  }, [first.data]);

  const loadMore = async () => {
    setAppending(true);
    setAppendError(null);
    try {
      const res = await api.browse(kind, section, genre, loadedPage + 1);
      if (res.results.length === 0) {
        setExhausted(true);
      } else {
        setItems((prev) => [...prev, ...res.results]);
        setLoadedPage((p) => p + 1);
      }
    } catch (e) {
      setAppendError(String(e));
    } finally {
      setAppending(false);
    }
  };

  const openItem = async (tmdbId: number) => {
    setPending(tmdbId);
    try {
      if (kind === "movie") {
        const movie = await api.importMovie(tmdbId);
        go(router, `/movie/${movie.id}`);
      } else {
        const show = await api.importShow(tmdbId);
        go(router, `/show/${show.id}`);
      }
    } finally {
      setPending(null);
    }
  };

  const meta = titleFor(
    kind,
    section,
    genreName.data?.genres.find((g) => g.id === genre)?.name ?? null,
  );

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-8">
      <header>
        <h1 className="font-display text-2xl tracking-wide">{meta.heading}</h1>
        <p className="text-sm text-[#5b6b84]">{meta.sub}</p>
      </header>

      {first.isError && (
        <p className="neu-inset px-6 py-8 text-sm text-red-600">
          {String(first.error ?? "Could not load titles.")}
        </p>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {items.map((r: SearchResult & TmdbTvResult, i: number) => {
          const title = (kind === "movie" ? r.title : r.name) ?? "Untitled";
          const year = ((kind === "movie" ? r.release_date : r.first_air_date) || "").slice(0, 4);
          const poster = posterUrl(r.poster_path);
          return (
            <button
              key={`${kind}-${r.id}`}
              type="button"
              onClick={() => openItem(r.id)}
              disabled={pending === r.id}
              className="neu card-lift mount-in p-2.5 pb-3 text-left disabled:opacity-60"
              style={{ animationDelay: `${Math.min(i % 20, 10) * 40}ms` }}
              aria-label={`View ${title}`}
            >
              <span className="relative block h-56 w-full overflow-hidden rounded-xl sm:h-64">
                {poster ? (
                  <Image
                    src={poster}
                    alt=""
                    fill
                    sizes="(max-width: 640px) 45vw, (max-width: 1024px) 30vw, 200px"
                    className="object-cover"
                    loading="lazy"
                  />
                ) : (
                  <span className="neu-inset flex h-full w-full items-center justify-center">
                    <Icon name={kind === "movie" ? "film" : "tv"} size={22} />
                  </span>
                )}
              </span>
              <span className="mt-1.5 block truncate text-[13px] font-medium">{title}</span>
              {year && (
                <span className="flex items-center gap-1 text-[11px] text-[#5b6b84]">
                  <Icon name="calendar" size={11} />
                  {year}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {first.isPending && items.length === 0 && (
        <div className="neu-inset shimmer px-6 py-8" aria-busy>
          <p className="text-sm text-[#5b6b84]">Loading…</p>
        </div>
      )}

      {appending && (
        <div className="neu-inset shimmer px-6 py-8" aria-busy>
          <p className="text-sm text-[#5b6b84]">Loading more…</p>
        </div>
      )}

      {appendError && (
        <p className="text-center text-sm text-red-600">{appendError}</p>
      )}

      {!first.isPending && !appending && !exhausted && items.length > 0 && section !== "awarded" && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={loadMore}
            className="neu flex items-center gap-2 px-8 py-3 text-sm font-medium"
          >
            <Icon name="plus" size={15} /> Load more
          </button>
        </div>
      )}
      {exhausted && (
        <p className="text-center text-sm text-[#5b6b84]">You've reached the end of the shelf.</p>
      )}
    </div>
  );
}

export default function BrowsePage() {
  return (
    <Suspense>
      <BrowseGrid />
    </Suspense>
  );
}
