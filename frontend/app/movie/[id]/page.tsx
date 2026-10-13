"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, backdropUrl, posterUrl, type EntryPatch, type LibraryStatus } from "@/lib/api";
import { patchCached, removeCached } from "@/lib/collection";
import { Row } from "@/components/Row";
import { Icon } from "@/components/icons";
import { EntryControls } from "@/components/EntryControls";

export default function MovieDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const validId = Number.isInteger(id) && id > 0;
  const [trailerOpen, setTrailerOpen] = useState(false);
  const [pending, setPending] = useState<number | null>(null);

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
      router.push(`/movie/${imported.id}`);
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
  const backdrop = backdropUrl(data.backdrop_path);
  const poster = posterUrl(data.poster_path);
  const trailer = (videos.data?.results ?? []).find(
    (v) => v.site === "YouTube" && (v.type === "Trailer" || v.type === "Teaser"),
  );
  const facts = [
    data.release_date
      ? { icon: "calendar" as const, label: "Release", value: data.release_date }
      : null,
    data.runtime ? { icon: "clock" as const, label: "Runtime", value: `${data.runtime} min` } : null,
    data.original_language
      ? { icon: "compass" as const, label: "Language", value: data.original_language.toUpperCase() }
      : null,
    data.vote_average != null
      ? {
          icon: "star" as const,
          label: "TMDB rating",
          value: `★ ${data.vote_average.toFixed(1)}${data.vote_count ? ` (${data.vote_count.toLocaleString()} votes)` : ""}`,
        }
      : null,
  ].filter(Boolean);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-8">
      <Link href="/" className="flex w-fit items-center gap-1.5 text-sm text-[#5b6b84] hover:underline">
        <Icon name="arrowLeft" size={15} /> Back home
      </Link>

      <section className="neu overflow-hidden" aria-label={data.title}>
        <div className="relative min-h-[320px] sm:min-h-[420px]">
          {backdrop && (
            <Image
              src={backdrop}
              alt=""
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 1024px"
              className="object-cover"
            />
          )}
          <div className="hero-scrim absolute inset-0" aria-hidden />
          <div className="hero-scrim-bottom absolute inset-x-0 bottom-0 h-20" aria-hidden />
          {trailer && (
            <button
              type="button"
              onClick={() => setTrailerOpen(true)}
              aria-label={`Play trailer for ${data.title}`}
              className="neu absolute top-1/2 left-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-2 !rounded-full px-6 py-3 text-sm font-semibold"
            >
              <Icon name="play" size={18} filled /> Trailer
            </button>
          )}
        </div>

        <div className="relative flex flex-col gap-5 p-6 sm:flex-row sm:gap-7 sm:p-8">
          {poster ? (
            <Image
              src={poster}
              alt={data.title}
              width={220}
              height={330}
              className="-mt-24 w-36 flex-shrink-0 rounded-xl object-cover shadow-lg sm:-mt-32 sm:w-52"
            />
          ) : (
            <div className="neu-inset -mt-24 flex h-52 w-36 flex-shrink-0 items-center justify-center rounded-xl sm:-mt-32 sm:h-72 sm:w-52" aria-hidden>
              <Icon name="film" size={28} />
            </div>
          )}
          <div className="flex min-w-0 flex-1 flex-col justify-center sm:pt-2">
            {data.award_label && (
              <p className="mb-2 flex w-fit items-center gap-1.5 rounded-full bg-[#5457d6]/10 px-3 py-1 text-[11px] font-semibold tracking-wide text-[#5457d6] uppercase">
                <Icon name="trophy" size={12} /> {data.award_label}
              </p>
            )}
            <h1 className="font-display text-3xl leading-tight tracking-wide text-balance sm:text-5xl">
              {data.title}
            </h1>
            {data.tagline && (
              <p className="mt-2 text-sm text-[#5b6b84] italic">“{data.tagline}”</p>
            )}
            <p className="mt-2 text-sm font-medium text-[#5b6b84]">
              {[data.release_year ? String(data.release_year) : null, data.runtime ? `${data.runtime} min` : null]
                .filter(Boolean)
                .join("  •  ")}
            </p>
            {data.genres.length > 0 && (
              <ul className="mt-3 flex flex-wrap gap-2" aria-label="Genres">
                {data.genres.map((genre) => (
                  <li key={genre.id} className="neu-inset px-3 py-1 text-xs font-medium">
                    {genre.name}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      <EntryControls
        entry={
          entry
            ? { status: entry.status, is_favorite: entry.is_favorite }
            : null
        }
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

      {data.overview && (
        <section className="neu p-6" aria-label="Story">
          <h2 className="text-sm font-semibold tracking-wide uppercase">Story</h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed">{data.overview}</p>
        </section>
      )}

      {facts.length > 0 && (
        <section className="neu grid grid-cols-2 gap-3 p-5 sm:grid-cols-4" aria-label="Facts">
          {facts.map((fact) =>
            fact ? (
              <div key={fact.label} className="neu-inset flex items-center gap-3 px-4 py-3">
                <Icon name={fact.icon} size={18} />
                <span>
                  <span className="block text-[11px] text-[#5b6b84]">{fact.label}</span>
                  <span className="block truncate text-sm font-medium">{fact.value}</span>
                </span>
              </div>
            ) : null,
          )}
        </section>
      )}

      {(credits.data?.cast ?? []).length > 0 && (
        <section aria-label="Cast">
          <h2 className="mb-3 text-lg font-semibold tracking-tight">Cast</h2>
          <div className="no-scrollbar -mx-1 flex gap-4 overflow-x-auto px-1 pt-2 pb-4">
            {(credits.data?.cast ?? []).slice(0, 12).map((person) => (
              <div key={person.id} className="neu w-28 flex-shrink-0 p-2 pb-3 text-center">
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
        <div
          role="dialog"
          aria-modal
          aria-label={`Trailer for ${data.title}`}
          onClick={() => setTrailerOpen(false)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-[#2d3a4f]/60 p-4"
        >
          <div
            className="neu w-full max-w-3xl overflow-hidden p-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-2 flex items-center justify-between px-1">
              <p className="truncate text-sm font-medium">{trailer.name}</p>
              <button
                type="button"
                onClick={() => setTrailerOpen(false)}
                aria-label="Close trailer"
                className="neu p-1.5"
              >
                <Icon name="x" size={15} />
              </button>
            </div>
            <div className="aspect-video w-full overflow-hidden rounded-xl">
              <iframe
                src={`https://www.youtube.com/embed/${trailer.key}?autoplay=1&rel=0`}
                title={trailer.name}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                className="h-full w-full"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
