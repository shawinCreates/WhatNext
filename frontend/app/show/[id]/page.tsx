"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, backdropUrl, posterUrl, type EntryPatch, type LibraryStatus } from "@/lib/api";
import { patchCached, removeCached } from "@/lib/collection";
import { Row } from "@/components/Row";
import { Icon } from "@/components/icons";
import { EntryControls } from "@/components/EntryControls";

export default function ShowDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const validId = Number.isInteger(id) && id > 0;
  const [trailerOpen, setTrailerOpen] = useState(false);
  const [pending, setPending] = useState<number | null>(null);

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
      router.push(`/show/${imported.id}`);
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
  const backdrop = backdropUrl(data.backdrop_path);
  const poster = posterUrl(data.poster_path);
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
          value: `★ ${data.vote_average.toFixed(1)}${data.vote_count ? ` (${data.vote_count.toLocaleString()} votes)` : ""}`,
        }
      : null,
  ].filter(Boolean);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-8">
      <Link href="/shows" className="flex w-fit items-center gap-1.5 text-sm text-[#5b6b84] hover:underline">
        <Icon name="arrowLeft" size={15} /> Back to shows
      </Link>

      <section className="neu overflow-hidden" aria-label={data.name}>
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
              aria-label={`Play trailer for ${data.name}`}
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
              alt={data.name}
              width={220}
              height={330}
              className="-mt-24 w-36 flex-shrink-0 rounded-xl object-cover shadow-lg sm:-mt-32 sm:w-52"
            />
          ) : (
            <div className="neu-inset -mt-24 flex h-52 w-36 flex-shrink-0 items-center justify-center rounded-xl sm:-mt-32 sm:h-72 sm:w-52" aria-hidden>
              <Icon name="tv" size={28} />
            </div>
          )}
          <div className="flex min-w-0 flex-1 flex-col justify-center sm:pt-2">
            {data.is_anime && (
              <p className="mb-2 flex w-fit items-center gap-1.5 rounded-full bg-[#5457d6]/10 px-3 py-1 text-[11px] font-semibold tracking-wide text-[#5457d6] uppercase">
                <Icon name="sparkles" size={12} /> Anime
              </p>
            )}
            <h1 className="font-display text-3xl leading-tight tracking-wide text-balance sm:text-5xl">
              {data.name}
            </h1>
            {data.tagline && (
              <p className="mt-2 text-sm text-[#5b6b84] italic">“{data.tagline}”</p>
            )}
            <p className="mt-2 text-sm font-medium text-[#5b6b84]">
              {[
                data.release_year ? String(data.release_year) : null,
                data.seasons ? `${data.seasons} season${data.seasons === 1 ? "" : "s"}` : null,
              ]
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
        subtitle="Similar series"
        icon="sparkles"
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
        <div
          role="dialog"
          aria-modal
          aria-label={`Trailer for ${data.name}`}
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
