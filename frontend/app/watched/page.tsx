"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type LibraryEntry, type ShowEntry } from "@/lib/api";
import { removeCached } from "@/lib/collection";
import { ShelfGrid, type ShelfItem } from "@/components/ShelfGrid";
import { CountUp } from "@/components/CountUp";
import {
  CollectionToolbar,
  type MediaFilter,
  type SortKey,
} from "@/components/CollectionToolbar";

type Item =
  | { kind: "movie"; entry: LibraryEntry; title: string; year: number | null; updated: string }
  | { kind: "show"; entry: ShowEntry; title: string; year: number | null; updated: string };

function sortItems(items: Item[], sort: SortKey) {
  return [...items].sort((a, b) => {
    if (sort === "title") return a.title.localeCompare(b.title);
    if (sort === "year") return (b.year ?? -1) - (a.year ?? -1);
    return b.updated.localeCompare(a.updated);
  });
}

export default function WatchedPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [media, setMedia] = useState<MediaFilter>("all");
  const [sort, setSort] = useState<SortKey>("recent");

  const library = useQuery({ queryKey: ["library"], queryFn: api.library });
  const showsLibrary = useQuery({
    queryKey: ["shows-library"],
    queryFn: api.showsLibrary,
  });

  const remove = useMutation({
    mutationFn: ({ kind, id }: { kind: "movie" | "show"; id: number }): Promise<unknown> =>
      kind === "movie" ? api.deleteEntry(id) : api.deleteShowEntry(id),
    onMutate: ({ kind, id }) =>
      kind === "movie"
        ? removeCached(queryClient, ["library"], id)
        : removeCached(queryClient, ["shows-library"], id),
    onError: (_e, _v, rollback) => rollback?.(),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["library"] });
      queryClient.invalidateQueries({ queryKey: ["shows-library"] });
    },
  });

  const filtered = useMemo(() => {
    const all: Item[] = [
      ...(library.data ?? [])
        .filter((e) => e.status === "WATCHED")
        .map(
          (entry): Item => ({
            kind: "movie",
            entry,
            title: entry.movie.title,
            year: entry.movie.release_year,
            updated: entry.updated_at,
          }),
        ),
      ...(showsLibrary.data ?? [])
        .filter((e) => e.status === "WATCHED")
        .map(
          (entry): Item => ({
            kind: "show",
            entry,
            title: entry.show.name,
            year: entry.show.release_year,
            updated: entry.updated_at,
          }),
        ),
    ];
    const q = search.trim().toLowerCase();
    return all.filter(
      (i) =>
        (media === "all" || i.kind === media) &&
        (!q || i.title.toLowerCase().includes(q)),
    );
  }, [library.data, showsLibrary.data, search, media]);

  const toShelf = (i: Item): ShelfItem => ({
    key: `${i.kind}-${i.entry.id}`,
    title: i.title,
    year: i.year ? String(i.year) : undefined,
    badge: i.kind === "show" ? (i.entry.show.is_anime ? "Anime" : "Series") : undefined,
    posterPath: i.kind === "movie" ? i.entry.movie.poster_path : i.entry.show.poster_path,
    href: i.kind === "movie" ? `/movie/${i.entry.movie.id}` : `/show/${i.entry.show.id}`,
    overlay: {
      label: "Remove from watched",
      icon: "x",
      tone: "danger",
      onPress: () => remove.mutate({ kind: i.kind, id: i.entry.id }),
      pending: remove.isPending,
    },
  });

  const movies = sortItems(
    filtered.filter((i) => i.kind === "movie"),
    sort,
  );
  const shows = sortItems(
    filtered.filter((i) => i.kind === "show"),
    sort,
  );
  const total = movies.length + shows.length;
  const loading = library.isPending && showsLibrary.isPending;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-6 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl tracking-wide">Watched</h1>
          <p className="mt-1 text-sm text-[#5b6b84]">
            {loading ? (
              "Loading…"
            ) : (
              <>
                <CountUp value={total} /> title{total === 1 ? "" : "s"} · {movies.length} movies ·{" "}
                {shows.length} shows
              </>
            )}
          </p>
        </div>
      </header>

      <CollectionToolbar
        search={search}
        onSearch={setSearch}
        media={media}
        onMedia={setMedia}
        sort={sort}
        onSort={setSort}
      />

      {(library.isError || showsLibrary.isError) && (
        <p className="text-sm text-red-600">
          {String(library.error ?? showsLibrary.error)}
        </p>
      )}
      {remove.isError && (
        <p className="text-sm text-red-600">{String(remove.error)}</p>
      )}

      {loading ? (
        <div className="neu-inset shimmer px-6 py-12" aria-busy>
          <p className="text-sm text-[#5b6b84]">Loading your history…</p>
        </div>
      ) : (
        <>
          {(media === "all" || media === "movie") && (
            <section aria-label="Watched movies">
              <h2 className="mb-3 text-lg font-semibold tracking-tight">Movies</h2>
              <ShelfGrid
                items={movies.map(toShelf)}
                empty="No watched movies match — open any title and hit Watched."
              />
            </section>
          )}
          {(media === "all" || media === "show") && (
            <section aria-label="Watched shows">
              <h2 className="mb-3 text-lg font-semibold tracking-tight">Shows & anime</h2>
              <ShelfGrid
                items={shows.map(toShelf)}
                empty="No watched shows match."
              />
            </section>
          )}
        </>
      )}
    </div>
  );
}
