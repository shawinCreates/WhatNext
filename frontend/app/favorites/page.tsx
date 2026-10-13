"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  backdropUrl,
  type LibraryEntry,
  type ShowEntry,
} from "@/lib/api";
import { patchCached } from "@/lib/collection";
import { ShelfGrid, type ShelfItem } from "@/components/ShelfGrid";
import {
  CollectionToolbar,
  type MediaFilter,
  type SortKey,
} from "@/components/CollectionToolbar";
import { Icon } from "@/components/icons";

type Item =
  | { kind: "movie"; entry: LibraryEntry; title: string; year: number | null; updated: string }
  | { kind: "show"; entry: ShowEntry; title: string; year: number | null; updated: string };

export default function FavoritesPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [media, setMedia] = useState<MediaFilter>("all");
  const [sort, setSort] = useState<SortKey>("recent");

  const library = useQuery({ queryKey: ["library"], queryFn: api.library });
  const showsLibrary = useQuery({
    queryKey: ["shows-library"],
    queryFn: api.showsLibrary,
  });

  const unfavorite = useMutation({
    mutationFn: ({ kind, id }: { kind: "movie" | "show"; id: number }): Promise<unknown> =>
      kind === "movie"
        ? api.updateEntry(id, { is_favorite: false })
        : api.updateShowEntry(id, { is_favorite: false }),
    onMutate: ({ kind, id }) =>
      kind === "movie"
        ? patchCached(queryClient, ["library"], id, { is_favorite: false })
        : patchCached(queryClient, ["shows-library"], id, { is_favorite: false }),
    onError: (_e, _v, rollback) => rollback?.(),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["library"] });
      queryClient.invalidateQueries({ queryKey: ["shows-library"] });
    },
  });

  const items: Item[] = useMemo(() => {
    const all: Item[] = [
      ...(library.data ?? [])
        .filter((e) => e.is_favorite)
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
        .filter((e) => e.is_favorite)
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
    const filtered = all.filter(
      (i) =>
        (media === "all" || i.kind === media) &&
        (!q || i.title.toLowerCase().includes(q)),
    );
    return filtered.sort((a, b) => {
      if (sort === "title") return a.title.localeCompare(b.title);
      if (sort === "year") return (b.year ?? -1) - (a.year ?? -1);
      return b.updated.localeCompare(a.updated);
    });
  }, [library.data, showsLibrary.data, search, media, sort]);

  const toShelf = (i: Item): ShelfItem => ({
    key: `${i.kind}-${i.entry.id}`,
    title: i.title,
    year: i.year ? String(i.year) : undefined,
    posterPath: i.kind === "movie" ? i.entry.movie.poster_path : i.entry.show.poster_path,
    href: i.kind === "movie" ? `/movie/${i.entry.movie.id}` : `/show/${i.entry.show.id}`,
    overlay: {
      label: "Remove from favorites",
      icon: "star",
      filled: true,
      tone: "accent",
      onPress: () => unfavorite.mutate({ kind: i.kind, id: i.entry.id }),
      pending: unfavorite.isPending,
    },
  });

  const loading = library.isPending && showsLibrary.isPending;
  const spotlight = items.slice(0, 3);
  const rest = items.slice(3);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-6 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl tracking-wide">Favorites</h1>
          <p className="mt-1 text-sm text-[#5b6b84]">
            {loading ? "Loading…" : `${items.length} loved title${items.length === 1 ? "" : "s"}`}
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
      {unfavorite.isError && (
        <p className="text-sm text-red-600">{String(unfavorite.error)}</p>
      )}

      {loading ? (
        <div className="neu-inset shimmer px-6 py-12" aria-busy>
          <p className="text-sm text-[#5b6b84]">Loading your favorites…</p>
        </div>
      ) : items.length === 0 ? (
        <div className="neu p-8 text-center">
          <p className="mx-auto flex w-fit p-3" aria-hidden>
            <Icon name="star" size={26} />
          </p>
          <p className="mt-2 text-sm font-medium">No favorites yet</p>
          <p className="mx-auto mt-1 max-w-sm text-sm text-[#5b6b84]">
            Open any title and hit Favorite — your hall of fame builds here.
          </p>
          <Link href="/" className="neu mt-4 inline-block px-6 py-2 text-sm font-medium">
            Browse titles
          </Link>
        </div>
      ) : (
        <>
          {spotlight.length > 0 && (
            <section aria-label="Recently starred" className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {spotlight.map((i) => {
                const backdrop =
                  i.kind === "movie"
                    ? backdropUrl(i.entry.movie.backdrop_path, "w780")
                    : backdropUrl(i.entry.show.backdrop_path, "w780");
                const href =
                  i.kind === "movie"
                    ? `/movie/${i.entry.movie.id}`
                    : `/show/${i.entry.show.id}`;
                return (
                  <Link
                    key={`spot-${i.kind}-${i.entry.id}`}
                    href={href}
                    className="neu group relative block min-h-44 overflow-hidden p-5"
                    aria-label={`${i.title} — recently starred`}
                  >
                    {backdrop && (
                      <Image
                        src={backdrop}
                        alt=""
                        fill
                        sizes="(max-width: 768px) 100vw, 320px"
                        className="object-cover opacity-40 transition-opacity group-hover:opacity-55"
                        loading="lazy"
                      />
                    )}
                    <span className="relative flex h-full min-h-32 flex-col justify-end">
                      <span className="flex items-center gap-1.5 text-[11px] font-semibold tracking-[0.18em] text-[#5457d6] uppercase">
                        <Icon name="star" size={12} filled /> Recently starred
                      </span>
                      <span className="font-display mt-1 line-clamp-2 text-lg leading-snug">
                        {i.title}
                      </span>
                      {i.year && (
                        <span className="mt-0.5 text-xs text-[#5b6b84]">{i.year}</span>
                      )}
                    </span>
                  </Link>
                );
              })}
            </section>
          )}
          {rest.length > 0 && (
            <section aria-label="All favorites">
              <h2 className="mb-3 text-lg font-semibold tracking-tight">The collection</h2>
              <ShelfGrid items={rest.map(toShelf)} empty="" />
            </section>
          )}
        </>
      )}
    </div>
  );
}
