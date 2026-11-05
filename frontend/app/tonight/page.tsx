"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, backdropUrl, type Recommendation } from "@/lib/api";
import { DetailHero } from "@/components/DetailHero";
import { Icon } from "@/components/icons";

const HALF_HOUR = 1000 * 60 * 30;
const HOUR = 1000 * 60 * 60;

function reasonFor(r: Recommendation) {
  if (!r.personalized) return "A well-reviewed pick from the catalog.";
  const labels = r.reasons.map((x) => x.label.toLowerCase()).slice(0, 3);
  const liked = r.similar_liked.map((x) => x.title).slice(0, 2);
  if (labels.length === 0) return "Picked from your shelf patterns.";
  return `Because you like ${labels.join(", ")}${
    liked.length > 0 ? ` — similar to ${liked.join(", ")}` : ""
  }.`;
}

export default function TonightPage() {
  const queryClient = useQueryClient();
const [index, setIndex] = useState(0);

  const reco = useQuery({
    queryKey: ["recommendations", "tonight"],
    queryFn: () => api.recommendations("all", 10, "tonight"),
    staleTime: HALF_HOUR,
  });

  const tkeyOf = (r: Recommendation) =>
    `${r.kind === "movie" ? "m" : "s"}${r.id}`;

  const clickReco = useMutation({
    mutationFn: ({
      tkey,
      kind,
      titleId,
      position,
    }: {
      tkey: string;
      kind: string;
      titleId: number;
      position?: number;
    }) => api.recoClick(tkey, kind, titleId, position),
  });

  const logClick = ({
    tkey,
    kind,
    titleId,
    position,
  }: {
    tkey: string;
    kind: string;
    titleId: number;
    position?: number;
  }) => {
    clickReco.mutate({ tkey, kind, titleId, position });
  };

  const addToWatchlist = useMutation({
    mutationFn: async (r: Recommendation) => {
      if (r.kind === "movie") await api.addToLibrary(r.id, "WATCHLIST");
      else await api.addShowToLibrary(r.id, "WATCHLIST");
      logClick({ tkey: tkeyOf(r), kind: r.kind, titleId: r.id, position: r.rank });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendations"] });
      queryClient.invalidateQueries({ queryKey: ["library"] });
      queryClient.invalidateQueries({ queryKey: ["shows-library"] });
      setToast({ msg: "Added to watchlist", kind: "success" });
    },
  });

  const markWatched = useMutation({
    mutationFn: async ({
      r,
      rating,
    }: {
      r: Recommendation;
      rating: number;
    }) => {
      if (r.kind === "movie") await api.addToLibrary(r.id, "WATCHED", rating);
      else await api.addShowToLibrary(r.id, "WATCHED", rating);
      logClick({ tkey: tkeyOf(r), kind: r.kind, titleId: r.id, position: r.rank });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendations"] });
      queryClient.invalidateQueries({ queryKey: ["library"] });
      queryClient.invalidateQueries({ queryKey: ["shows-library"] });
      setToast({ msg: "Logged as watched", kind: "success" });
    },
  });

  const reject = useMutation({
    mutationFn: async (r: Recommendation) => {
      if (r.kind === "movie") await api.addToLibrary(r.id, "REJECTED");
      else await api.addShowToLibrary(r.id, "REJECTED");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendations"] });
      queryClient.invalidateQueries({ queryKey: ["library"] });
      queryClient.invalidateQueries({ queryKey: ["shows-library"] });
      setToast({ msg: "Noted — won't suggest again", kind: "info" });
    },
  });

  const [toast, setToast] = useState<{
    msg: string;
    kind: "success" | "info";
  } | null>(null);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2500);
    return () => clearTimeout(t);
  }, [toast]);

  const candidates = (reco.data?.results ?? []).filter((r) => r.backdrop_path);
  const active = candidates.length
    ? candidates[index % candidates.length]
    : undefined;
  useEffect(() => setIndex(0), [candidates.length]);

  const tmdbId = active?.tmdb_id;
  const credits = useQuery({
    queryKey: ["credits", "movie", tmdbId],
    queryFn: () => api.titleCredits("movie", tmdbId!),
    enabled: !!tmdbId && active?.kind === "movie",
    staleTime: HOUR,
  });

  if (!active) {
    return (
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-6 py-8">
        {reco.isPending ? (
          <div className="neu-inset shimmer px-6 py-16" aria-busy>
            <p className="text-sm text-[#5b6b84]">Picking tonight's titles…</p>
          </div>
        ) : reco.isError ? (
          <div className="neu-inset px-6 py-16">
            <p className="text-sm text-red-600">{String(reco.error)}</p>
          </div>
        ) : (
          <div className="neu p-8">
            <h2 className="font-display text-xl tracking-wide">
              Nothing left to suggest
            </h2>
            <p className="mt-2 max-w-lg text-sm text-[#5b6b84]">
              You've rated, saved, or rejected every title in the catalog.
              Import more from Browse.
            </p>
          </div>
        )}
        <footer className="flex justify-center pb-4">
          <p className="font-mono text-xs text-[#5b6b84]">
            WhatNext · movies, shows & anime
          </p>
        </footer>
      </div>
    );
  }

  const rejecting =
    reject.isPending &&
    reject.variables?.id === active?.id &&
    reject.variables?.kind === active?.kind;
  const adding =
    addToWatchlist.isPending &&
    addToWatchlist.variables?.id === active?.id &&
    addToWatchlist.variables?.kind === active?.kind;
  const watching =
    markWatched.isPending &&
    markWatched.variables?.r?.id === active?.id &&
    markWatched.variables?.r?.kind === active?.kind;
  const director =
    active.kind === "movie"
      ? (credits.data?.crew ?? []).find((c) => c.job === "Director")?.name
      : undefined;
  const voteText =
    active.vote_average != null
      ? `★ ${active.vote_average.toFixed(1)}${
          active.vote_count ? ` (${active.vote_count.toLocaleString()})` : ""
        }`
      : undefined;
  const facts = [
    active.release_date
      ? active.kind === "movie"
        ? { icon: "calendar" as const, label: "Release", value: active.release_date }
        : { icon: "calendar" as const, label: "First aired", value: active.release_date.slice(0, 4) }
      : null,
    active.kind === "movie"
      ? active.runtime
        ? { icon: "clock" as const, label: "Runtime", value: `${active.runtime} min` }
        : null
      : active.episodes
        ? { icon: "play" as const, label: "Episodes", value: String(active.episodes) }
        : null,
    active.original_language
      ? { icon: "compass" as const, label: "Language", value: active.original_language.toUpperCase() }
      : null,
    active.vote_average != null
      ? { icon: "star" as const, label: "TMDB rating", value: voteText ?? "" }
      : null,
  ].filter((f): f is { icon: "calendar" | "clock" | "compass" | "play" | "star"; label: string; value: string } => Boolean(f));

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-6 py-8">
      <DetailHero
        title={active.title}
        backdropPath={active.backdrop_path}
        kicker={active.award_label || (active.is_anime ? "Anime" : undefined)}
        genres={active.genres}
        overview={active.overview}
        metaYear={active.year ? String(active.year) : undefined}
        metaBadge={
          active.kind === "movie"
            ? active.runtime
              ? `${active.runtime} min`
              : undefined
            : active.seasons
              ? `${active.seasons} season${active.seasons === 1 ? "" : "s"}`
              : undefined
        }
        vote={voteText}
        creator={director
          ? { label: "Director", value: director }
          : active.created_by
            ? { label: "Creator", value: active.created_by }
            : undefined}
        facts={facts}
        shelf={
          <div className="flex flex-col gap-3">
            {active ? (
              <>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => addToWatchlist.mutate(active)}
                    disabled={adding}
                    title="Save to watchlist"
                    aria-label="Save to watchlist"
                    className={`neu pressable flex items-center gap-2 !rounded-full px-6 py-3 text-sm font-semibold ${adding ? "opacity-70" : ""}`}
                  >
                    <Icon name="bookmark" size={16} /> Add to watchlist
                  </button>
                </div>
                <section
                  aria-label="Already watched?"
                  className="flex items-center gap-2"
                >
                  <span className="shrink-0 text-xs text-[#5b6b84] leading-6">
                    Already watched?
                  </span>
                  <button
                    type="button"
                    onClick={() => markWatched.mutate({ r: active, rating: 9 })}
                    disabled={watching}
                    className="neu pressable px-4 py-2 text-xs font-semibold !rounded-full"
                  >
                    Liked it <span className="text-[#b98a1d]">★9</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => markWatched.mutate({ r: active, rating: 6 })}
                    disabled={watching}
                    className="neu pressable px-4 py-2 text-xs font-semibold !rounded-full"
                  >
                    It's OK <span className="text-[#5b6b84]">★6</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => markWatched.mutate({ r: active, rating: 3 })}
                    disabled={watching}
                    className="neu pressable px-4 py-2 text-xs font-semibold !rounded-full"
                  >
                    Hated it <span className="text-[#b98a1d]">★3</span>
                  </button>
                </section>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      setIndex((i) => (i + 1) % Math.max(candidates.length, 1))
                    }
                    className="neu pressable flex items-center gap-2 !rounded-full px-5 py-3 text-sm text-[#5b6b84]"
                    aria-label="Shuffle to another pick"
                  >
                    <Icon name="compass" size={15} /> Shuffle
                  </button>
                  <button
                    type="button"
                    onClick={() => reject.mutate(active)}
                    disabled={rejecting}
                    className="neu pressable flex items-center gap-2 !rounded-full px-5 py-3 text-sm text-[#5b6b84] hover:text-red-600 disabled:opacity-50"
                    aria-label="Not for me — hide from recommendations"
                  >
                    <Icon name="x" size={15} />
                    {rejecting ? "Rejecting…" : "Not for me"}
                  </button>
                </div>
              </>
            ) : null}
          </div>
        }
      />

      {reject.isError && (
        <p className="text-sm text-red-600">{String(reject.error)}</p>
      )}

      {toast && (
        <p className={`text-sm ${toast.kind === "success" ? "text-[#5457d6]" : "text-[#5b6b84]"}`}>
          {toast.msg}
        </p>
      )}

      <footer className="flex justify-center pb-4">
        <p className="font-mono text-xs text-[#5b6b84]">
          WhatNext · movies, shows & anime
        </p>
      </footer>
    </div>
  );
}
