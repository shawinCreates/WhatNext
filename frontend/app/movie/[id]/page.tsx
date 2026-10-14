"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, type EntryPatch, type LibraryStatus } from "@/lib/api";
import { patchCached, removeCached } from "@/lib/collection";
import { go, useInView } from "@/lib/motion";
import { Row } from "@/components/Row";
import { Icon } from "@/components/icons";
import { DetailHero } from "@/components/DetailHero";
import { RatingNotes } from "@/components/RatingNotes";
import { ShelfActions } from "@/components/ShelfActions";
import { TrailerModal } from "@/components/TrailerModal";
import { ScrollProgress } from "@/components/ScrollProgress";

export default function MovieDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const validId = Number.isInteger(id) && id > 0;
  const [trailerOpen, setTrailerOpen] = useState(false);
  const [pending, setPending] = useState<number | null>(null);
  const castReveal = useInView<HTMLElement>();

  const movie = useQuery({
    queryKey: ["movie", id],
    queryFn: () => api.movie(id),
    enabled: validId,
  });
  const library = useQuery({ queryKey: ["library"], queryFn: api.library });

  const add = useMutation({
    mutationFn: (status: LibraryStatus) => api.addToLibrary(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["library"] }),
  });
  const update = useMutation({
    mutationFn: ({ entryId, patch }: { entryId: number; patch: EntryPatch }) =>
      api.updateEntry(entryId, patch),
    onMutate: ({ entryId, patch }) => patchCached(queryClient, ["library"], entryId, patch),
    onError: (_e, _v, rollback) => rollback?.(),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["library"] }),
  });
  const remove = useMutation({
    mutationFn: (entryId: number) => api.deleteEntry(entryId),
    onMutate: (entryId) => removeCached(queryClient, ["library"], entryId),
    onError: (_e, _v, rollback) => rollback?.(),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["library"] }),
  });

  const tmdbId = movie.data?.tmdb_id;
  const videos = useQuery({
    queryKey: ["videos", "movie", tmdbId],
    queryFn: () => api.titleVideos("movie", tmdbId!),
    enabled: !!tmdbId,
    staleTime: 1000 * 60 * 60,
  });
  const credits = useQuery({
    queryKey: ["credits", "movie", tmdbId],
    queryFn: () => api.titleCredits("movie", tmdbId!),
    enabled: !!tmdbId,
    staleTime: 1000 * 60 * 60,
  });
  const similar = useQuery({
    queryKey: ["similar", "movie", tmdbId],
    queryFn: () => api.titleSimilar("movie", tmdbId!),
    enabled: !!tmdbId,
    staleTime: 1000 * 60 * 30,
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
      const imported = await api.importMovie(similarTmdbId);
      go(router, `/movie/${imported.id}`);
    } finally {
      setPending(null);
    }
  };

  if (!validId) {
    return (
      <div className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <p className="neu-inset px-6 py-8 text-sm">Invalid movie id.</p>
      </div>
    );
  }

  if (movie.isPending) {
    return (
      <div className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <div className="neu-inset shimmer px-6 py-16" aria-busy>
          <p className="text-sm text-[#5b6b84]">Loading movie…</p>
        </div>
      </div>
    );
  }

  if (movie.isError || !movie.data) {
    return (
      <div className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <Link href="/" className="flex w-fit items-center gap-1.5 text-sm text-[#5b6b84] hover:underline">
          <Icon name="arrowLeft" size={15} /> Back home
        </Link>
        <p className="neu-inset mt-4 px-6 py-8 text-sm text-red-600">
          {String(movie.error ?? "Movie not found.")}
        </p>
      </div>
    );
  }

  const data = movie.data;
  const entry = library.data?.find((item) => item.movie.id === data.id);
  const trailer = (videos.data?.results ?? []).find(
    (v) => v.site === "YouTube" && (v.type === "Trailer" || v.type === "Teaser"),
  );
  const director = (credits.data?.crew ?? []).find((c) => c.job === "Director")?.name;
  const facts = [
    data.release_date ? { icon: "calendar" as const, label: "Release", value: data.release_date } : null,
    data.runtime ? { icon: "clock" as const, label: "Runtime", value: `${data.runtime} min` } : null,
    data.original_language
      ? { icon: "compass" as const, label: "Language", value: data.original_language.toUpperCase() }
      : null,
    data.vote_average != null
      ? {
          icon: "star" as const,
          label: "TMDB rating",
          value: `★ ${data.vote_average.toFixed(1)}${data.vote_count ? ` (${data.vote_count.toLocaleString()})` : ""}`,
        }
      : null,
  ].filter((f): f is { icon: "calendar" | "clock" | "compass" | "star"; label: string; value: string } => Boolean(f));

  return (
    <div className="relative mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-6 py-8">
      <ScrollProgress />
      <Link href="/" className="flex w-fit items-center gap-1.5 text-sm text-[#5b6b84] hover:underline">
        <Icon name="arrowLeft" size={15} /> Back home
      </Link>

      <DetailHero
        title={data.title}
        backdropPath={data.backdrop_path}
        kicker={data.award_label || undefined}
        genres={data.genres}
        overview={data.overview}
        metaYear={data.release_year ? String(data.release_year) : undefined}
        metaBadge={data.runtime ? `${data.runtime} min` : undefined}
        vote={
          data.vote_average != null
            ? `${data.vote_average.toFixed(1)}${data.vote_count ? ` (${data.vote_count.toLocaleString()})` : ""}`
            : undefined
        }
        creator={director ? { label: "Director", value: director } : undefined}
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

      <RatingNotes
        entry={entry ? { rating: entry.rating, personal_note: entry.personal_note } : null}
        onUpdate={(patch) => entry && update.mutate({ entryId: entry.id, patch })}
        busy={update.isPending}
        error={update.isError ? String(update.error) : null}
      />

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
        subtitle="Similar titles"
        icon="sparkles"
        hoverPlay
        items={(similar.data?.results ?? []).slice(0, 12).map((r) => ({
          key: `sim-${r.id}`,
          title: r.title || r.name || "Untitled",
          year: ((r.release_date || r.first_air_date) || "").slice(0, 4) || undefined,
          posterPath: r.poster_path,
          onSelect: () => openSimilar(r.id),
          selectPending: pending === r.id,
        }))}
        empty="No similar titles found."
      />

      {trailerOpen && trailer && (
        <TrailerModal
          title={data.title}
          videoName={trailer.name}
          videoKey={trailer.key}
          onClose={() => setTrailerOpen(false)}
        />
      )}
    </div>
  );
}
