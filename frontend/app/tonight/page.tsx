"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, backdropUrl, type Recommendation } from "@/lib/api";
import { go } from "@/lib/motion";
import { DetailHero } from "@/components/DetailHero";
import { TrailerModal } from "@/components/TrailerModal";
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
  const router = useRouter();
  const queryClient = useQueryClient();
  const [index, setIndex] = useState(0);
  const [trailerOpen, setTrailerOpen] = useState(false);

  const reco = useQuery({
    queryKey: ["recommendations"],
    queryFn: () => api.recommendations("all", 10),
    staleTime: HALF_HOUR,
  });

  const reject = useMutation({
    mutationFn: async (r: Recommendation) => {
      if (r.kind === "movie") await api.addToLibrary(r.id, "REJECTED");
      else await api.addShowToLibrary(r.id, "REJECTED");
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["recommendations"] }),
  });

  const candidates = (reco.data?.results ?? []).filter((r) => r.backdrop_path);
  const active = candidates.length
    ? candidates[index % candidates.length]
    : undefined;
  useEffect(() => setIndex(0), [candidates.length]);

  const tmdbId = active?.tmdb_id;
  const media = active?.kind === "movie" ? "movie" : "tv";
  const videos = useQuery({
    queryKey: ["videos", media, tmdbId],
    queryFn: () => api.titleVideos(media, tmdbId!),
    enabled: !!tmdbId,
    staleTime: HOUR,
  });
  const credits = useQuery({
    queryKey: ["credits", "movie", tmdbId],
    queryFn: () => api.titleCredits("movie", tmdbId!),
    enabled: !!tmdbId && active?.kind === "movie",
    staleTime: HOUR,
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTrailerOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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
    reject.variables?.id === active.id &&
    reject.variables?.kind === active.kind;
  const trailer = (videos.data?.results ?? []).find(
    (v) => v.site === "YouTube" && (v.type === "Trailer" || v.type === "Teaser"),
  );
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
        onTrailer={trailer ? () => setTrailerOpen(true) : undefined}
        shelf={
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() =>
                go(
                  router,
                  active.kind === "movie" ? `/movie/${active.id}` : `/show/${active.id}`,
                )
              }
              className="neu pressable flex items-center gap-2 !rounded-full px-6 py-3 text-sm font-semibold"
            >
              <Icon name="play" size={16} filled /> Watch tonight
            </button>
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
        }
      />

      {reject.isError && (
        <p className="text-sm text-red-600">{String(reject.error)}</p>
      )}

      {trailerOpen && trailer && (
        <TrailerModal
          title={active.title}
          videoName={trailer.name}
          videoKey={trailer.key}
          onClose={() => setTrailerOpen(false)}
        />
      )}

      <footer className="flex justify-center pb-4">
        <p className="font-mono text-xs text-[#5b6b84]">
          WhatNext · movies, shows & anime
        </p>
      </footer>
    </div>
  );
}
