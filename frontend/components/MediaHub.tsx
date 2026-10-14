"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import {
  api,
  backdropUrl,
  type BrowseSection,
  type MediaKind,
  type SearchResult,
  type TmdbTvResult,
} from "@/lib/api";
import { go } from "@/lib/motion";
import { Hero, type HeroSlide } from "@/components/Hero";
import { Row, type RailItem } from "@/components/Row";

type TmdbItem = SearchResult & TmdbTvResult;

const HALF_HOUR = 1000 * 60 * 30;

function titleOf(item: TmdbItem) {
  return item.title || item.name || "Untitled";
}

function yearOf(item: TmdbItem) {
  return (item.release_date || item.first_air_date || "").slice(0, 4) || undefined;
}

import type { IconName } from "@/components/icons";

const SECTION_META: {
  section: BrowseSection;
  title: string;
  subtitle: string;
  icon: IconName;
}[] = [
  { section: "trending", title: "Trending now", subtitle: "What everyone is watching", icon: "flame" },
  { section: "latest", title: "Latest", subtitle: "Fresh releases and airings", icon: "sparkles" },
  { section: "upcoming", title: "Upcoming", subtitle: "On the horizon", icon: "calendar" },
  { section: "top_rated", title: "Top rated", subtitle: "Highest rated by viewers", icon: "star" },
  { section: "awarded", title: "Award winners", subtitle: "Acclaimed and decorated", icon: "trophy" },
];

export function MediaHub({
  kind,
  heading,
  subheading,
}: {
  kind: MediaKind;
  heading: string;
  subheading: string;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const focusSection = searchParams.get("section") as BrowseSection | null;
  const focusGenre = Number(searchParams.get("genre")) || null;
  const [pending, setPending] = useState<number | null>(null);
  const isMovie = kind === "movie";

  const genreList = useQuery({
    queryKey: ["genres", kind],
    queryFn: () => api.genres(isMovie ? "movie" : "tv"),
    staleTime: HALF_HOUR,
  });

  const sections = SECTION_META.map(({ section }) => ({
    // eslint-disable-next-line react-hooks/rules-of-hooks
    query: useQuery({
      queryKey: ["browse", kind, section],
      queryFn: () => api.browse(kind, section),
      staleTime: HALF_HOUR,
    }),
    section,
  }));

  const openItem = async (tmdbId: number) => {
    setPending(tmdbId);
    try {
      if (isMovie) {
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

  const toRail = (item: TmdbItem): RailItem => ({
    key: `tmdb-${item.id}`,
    title: titleOf(item),
    year: yearOf(item),
    posterPath: item.poster_path,
    onSelect: () => openItem(item.id),
    selectPending: pending === item.id,
  });

  const heroPool = (["trending", "top_rated"] as BrowseSection[]).flatMap(
    (s) => sections.find((x) => x.section === s)?.query.data?.results ?? [],
  );
  const slides: HeroSlide[] = heroPool
    .filter((item) => item.backdrop_path)
    .slice(0, 7)
    .map((item) => ({
      key: `hero-${item.id}`,
      title: titleOf(item),
      meta: yearOf(item),
      overview: item.overview,
      backdrop: backdropUrl(item.backdrop_path),
      badge: `Featured • ${heading}`,
      onOpen: () => openItem(item.id),
      opening: pending === item.id,
    }));

  const loading = sections.every((s) => s.query.isPending);

  // Mood tiles deep-link here with ?section= / ?genre= — honor by ordering first.
  const ordered = [...sections].sort((a, b) =>
    a.section === focusSection ? -1 : b.section === focusSection ? 1 : 0,
  );
  const allGenres = genreList.data?.genres ?? [];
  const orderedGenres = [...allGenres]
    .sort((a, b) => (a.id === focusGenre ? -1 : b.id === focusGenre ? 1 : 0))
    .slice(0, 6);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-6 py-8">
      <header>
        <h1 className="font-display text-2xl tracking-wide">{heading}</h1>
        <p className="text-sm text-[#5b6b84]">{subheading}</p>
      </header>

      {loading && (
        <div className="neu-inset px-6 py-10" aria-busy>
          <p className="text-sm text-[#5b6b84]">Loading {heading}…</p>
        </div>
      )}
      {!loading && slides.length > 0 && <Hero slides={slides} />}

      {ordered.map(({ query, section }) => {
        const meta = SECTION_META.find((m) => m.section === section)!;
        if (query.isError)
          return (
            <p key={section} className="text-sm text-[#5b6b84]">
              {meta.title} is unavailable right now.
            </p>
          );
        return (
          <Row
            key={section}
            title={meta.title}
            subtitle={meta.subtitle}
            icon={meta.icon}
            viewAllHref={`/browse?media=${kind}&section=${section}`}
            items={(query.data?.results ?? []).slice(0, 12).map(toRail)}
            empty={`No ${meta.title.toLowerCase()} right now.`}
          />
        );
      })}

      {orderedGenres.map((genre) => (
        <GenreRow key={genre.id} kind={kind} genre={genre} toRail={toRail} />
      ))}
    </div>
  );
}

function GenreRow({
  kind,
  genre,
  toRail,
}: {
  kind: MediaKind;
  genre: { id: number; name: string };
  toRail: (item: TmdbItem) => RailItem;
}) {
  const query = useQuery({
    queryKey: ["browse", kind, "genre", genre.id],
    queryFn: () => api.browse(kind, "genre", genre.id),
    staleTime: HALF_HOUR,
  });
  if (query.isError || (query.data && query.data.results.length === 0))
    return null;
  return (
    <Row
      title={genre.name}
      viewAllHref={`/browse?media=${kind}&section=genre&genre=${genre.id}`}
      items={(query.data?.results ?? []).slice(0, 12).map(toRail)}
      empty=""
    />
  );
}
