"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type EntryPatch, type LibraryStatus } from "@/lib/api";
import { patchCached, removeCached } from "@/lib/collection";
import { go, useInView } from "@/lib/motion";
import { Row } from "@/components/Row";
import { Icon } from "@/components/icons";
import { DetailHero } from "@/components/DetailHero";
import { ShelfActions } from "@/components/ShelfActions";
import { TrailerModal } from "@/components/TrailerModal";
import { ScrollProgress } from "@/components/ScrollProgress";

export default function ShowDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const validId = Number.isInteger(id) && id > 0;
  const [trailerOpen, setTrailerOpen] = useState(false);
  const [pending, setPending] = useState<number | null>(null);
  const [season, setSeason] = useState(1);
  const castReveal = useInView<HTMLElement>();

  const show = useQuery({
    queryKey: ["show", id],
    queryFn: () => api.show(id),
    enabled: validId,
  });
  const library = useQuery({ queryKey: ["shows-library"], queryFn: api.showsLibrary });

  const add = useMutation({
    mutationFn: (status: LibraryStatus) => api.addShowToLibrary(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["shows-library"] }),
  });
  const update = useMutation({
    mutationFn: ({ entryId, patch }: { entryId: number; patch: EntryPatch }) =>
      api.updateShowEntry(entryId, patch),
    onMutate: ({ entryId, patch }) => patchCached(queryClient, ["shows-library"], entryId, patch),
    onError: (_e, _v, rollback) => rollback?.(),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["shows-library"] }),
  });
  const remove = useMutation({
    mutationFn: (entryId: number) => api.deleteShowEntry(entryId),
    onMutate: (entryId) => removeCached(queryClient, ["shows-library"], entryId),
    onError: (_e, _v, rollback) => rollback?.(),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["shows-library"] }),
  });

  const tmdbId = show.data?.tmdb_id;
  const videos = useQuery({
    queryKey: ["videos", "tv", tmdbId],
    queryFn: () => api.titleVideos("tv", tmdbId!),
    enabled: !!tmdbId,
    staleTime: 1000 * 60 * 60,
  });
  const credits = useQuery({
    queryKey: ["credits", "tv", tmdbId],
    queryFn: () => api.titleCredits("tv", tmdbId!),
    enabled: !!tmdbId,
    staleTime: 1000 * 60 * 60,
  });
  const similar = useQuery({
    queryKey: ["similar", "tv", tmdbId],
    queryFn: () => api.titleSimilar("tv", tmdbId!),
    enabled: !!tmdbId,
    staleTime: 1000 * 60 * 30,
  });
  const seasonData = useQuery({
    queryKey: ["season", tmdbId, season],
    queryFn: () => api.tvSeason(tmdbId!, season),
    enabled: !!tmdbId,
    staleTime: 1000 * 60 * 60,
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTrailerOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const openSimilar = async (similarTmdbId: number) => {
    setPending(similarTmdbId);
    try {
      const imported = await api.importShow(similarTmdbId);
      go(router, `/show/${imported.id}`);
    } finally {
      setPending(null);
    }
  };

  if (!validId) {
    return (
      <div className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <p className="neu-inset px-6 py-8 text-sm">Invalid show id.</p>
      </div>
    );
  }

  if (show.isPending) {
    return (
      <div className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <div className="neu-inset shimmer px-6 py-16" aria-busy>
          <p className="text-sm text-[#5b6b84]">Loading show…</p>
        </div>
      </div>
    );
  }

  if (show.isError || !show.data) {
    return (
      <div className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <Link href="/shows" className="flex w-fit items-center gap-1.5 text-sm text-[#5b6b84] hover:underline">
          <Icon name="arrowLeft" size={15} /> Back to shows
        </Link>
        <p className="neu-inset mt-4 px-6 py-8 text-sm text-red-600">
          {String(show.error ?? "Show not found.")}
        </p>
      </div>
    );
  }

  const data = show.data;
  const entry = library.data?.find((item) => item.show.id === data.id);
  const trailer = (videos.data?.results ?? []).find(
    (v) => v.site === "YouTube" && (v.type === "Trailer" || v.type === "Teaser"),
  );
  const facts = [
    data.release_year ? { icon: "calendar" as const, label: "First aired", value: String(data.release_year) } : null,
    data.seasons ? { icon: "film" as const, label: "Seasons", value: String(data.seasons) } : null,
    data.episodes ? { icon: "play" as const, label: "Episodes", value: String(data.episodes) } : null,
    data.vote_average != null
      ? {
          icon: "star" as const,
          label: "TMDB rating",
          value: `★ ${data.vote_average.toFixed(1)}${data.vote_count ? ` (${data.vote_count.toLocaleString()})` : ""}`,
        }
      : null,
  ].filter((f): f is { icon: "calendar" | "film" | "play" | "star"; label: string; value: string } => Boolean(f));

  const seasonCount = data.seasons ?? 0;
  const episodes = seasonData.data?.episodes ?? [];

  return (
    <div className="relative mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-6 py-8">
      <ScrollProgress />
      <Link href="/shows" className="flex w-fit items-center gap-1.5 text-sm text-[#5b6b84] hover:underline">
        <Icon name="arrowLeft" size={15} /> Back to shows
      </Link>

      <DetailHero
        title={data.name}
        backdropPath={data.backdrop_path}
        kicker={data.is_anime ? "Anime" : undefined}
        genres={data.genres}
        overview={data.overview}
        metaYear={data.release_year ? String(data.release_year) : undefined}
        metaBadge={data.seasons ? `${data.seasons} season${data.seasons === 1 ? "" : "s"}` : undefined}
        vote={
          data.vote_average != null
            ? `${data.vote_average.toFixed(1)}${data.vote_count ? ` (${data.vote_count.toLocaleString()})` : ""}`
            : undefined
        }
        creator={data.created_by ? { label: "Creator", value: data.created_by } : undefined}
        facts={facts}
        onTrailer={trailer ? () => setTrailerOpen(true) : undefined}
        shelf={
          <ShelfActions
            entry={entry ? { status: entry.status, is_favorite: entry.is_favorite } : null}
            onAdd={(status) => add.mutate(status)}
            onUpdate={(patch) => entry && update.mutate({ entryId: entry.id, patch })}
            onRemove={() => entry && remove.mutate(entry.id)}
            busy={{ add: add.isPending, update: update.isPending, remove: remove.isPending }}
            error={
              add.isError || update.isError || remove.isError
                ? String(add.error ?? update.error ?? remove.error)
                : null
            }
          />
        }
      />

      {seasonCount > 0 && (
        <section aria-label="Episodes">
          <div className="mb-3 flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold tracking-tight">Episodes</h2>
            <select
              value={season}
              onChange={(e) => setSeason(Number(e.target.value))}
              aria-label="Select season"
              className="neu-inset px-3 py-2 text-sm outline-none"
            >
              {Array.from({ length: seasonCount }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  Season {n}
                </option>
              ))}
            </select>
          </div>
          {seasonData.isPending ? (
            <div className="neu-inset shimmer px-6 py-8" aria-busy>
              <p className="text-sm text-[#5b6b84]">Loading episodes…</p>
            </div>
          ) : seasonData.isError ? (
            <p className="text-sm text-[#5b6b84]">Episodes unavailable for this season.</p>
          ) : (
            <div className="no-scrollbar -mx-1 flex gap-5 overflow-x-auto px-1 pt-2 pb-4">
              {episodes.map((ep) => (
                <article key={ep.id} className="neu card-lift w-72 flex-shrink-0 p-2.5 pb-3 sm:w-80">
                  <div className="relative aspect-video w-full overflow-hidden rounded-xl">
                    {ep.still_path ? (
                      <Image
                        src={`https://image.tmdb.org/t/p/w500${ep.still_path}`}
                        alt={ep.name}
                        fill
                        sizes="320px"
                        className="object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="neu-inset flex h-full w-full items-center justify-center" aria-hidden>
                        <Icon name="play" size={20} />
                      </div>
                    )}
                    <span className="neu-inset absolute top-2 left-2 px-2.5 py-1 text-[11px] font-semibold">
                      E{ep.episode_number}
                    </span>
                    {ep.runtime ? (
                      <span className="neu-inset absolute right-2 bottom-2 px-2.5 py-1 text-[11px] font-medium">
                        {ep.runtime}m
                      </span>
                    ) : null}
                  </div>
                  <h3 className="mt-2 truncate px-1 text-sm font-semibold">{ep.name}</h3>
                  {ep.overview && (
                    <p className="line-clamp-2 px-1 text-xs leading-relaxed text-[#5b6b84]">
                      {ep.overview}
                    </p>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {(credits.data?.cast ?? []).length > 0 && (
        <section
          ref={castReveal.ref}
          className={`reveal ${castReveal.visible ? "visible" : ""}`}
          aria-label="Cast"
        >
          <h2 className="mb-3 text-lg font-semibold tracking-tight">Cast</h2>
          <div className="no-scrollbar -mx-1 flex gap-4 overflow-x-auto px-1 pt-2 pb-4">
            {(credits.data?.cast ?? []).slice(0, 12).map((person) => (
              <div key={person.id} className="neu card-lift w-28 flex-shrink-0 p-2 pb-3 text-center">
                {person.profile_path ? (
                  <Image
                    src={`https://image.tmdb.org/t/p/w185${person.profile_path}`}
                    alt={person.name}
                    width={96}
                    height={144}
                    loading="lazy"
                    className="h-36 w-full rounded-lg object-cover"
                  />
                ) : (
                  <div className="neu-inset flex h-36 w-full items-center justify-center rounded-lg" aria-hidden>
                    <Icon name="play" size={18} />
                  </div>
                )}
                <p className="mt-1.5 truncate text-xs font-medium">{person.name}</p>
                {person.character && (
                  <p className="truncate text-[11px] text-[#5b6b84]">{person.character}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <Row
        title="You may also like"
        subtitle="Similar series"
        icon="sparkles"
        hoverPlay
        items={(similar.data?.results ?? []).slice(0, 12).map((r) => ({
          key: `sim-${r.id}`,
          title: r.name || r.title || "Untitled",
          year: ((r.first_air_date || r.release_date) || "").slice(0, 4) || undefined,
          posterPath: r.poster_path,
          onSelect: () => openSimilar(r.id),
          selectPending: pending === r.id,
        }))}
        empty="No similar series found."
      />

      {trailerOpen && trailer && (
        <TrailerModal
          title={data.name}
          videoName={trailer.name}
          videoKey={trailer.key}
          onClose={() => setTrailerOpen(false)}
        />
      )}
    </div>
  );
}
