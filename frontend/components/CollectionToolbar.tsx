"use client";

import { Icon } from "@/components/icons";

export type MediaFilter = "all" | "movie" | "show";
export type SortKey = "recent" | "title" | "year";

export function CollectionToolbar({
  search,
  onSearch,
  media,
  onMedia,
  sort,
  onSort,
  sortOptions = [
    { id: "recent", label: "Recently logged" },
    { id: "title", label: "Title A–Z" },
    { id: "year", label: "Newest year" },
  ],
}: {
  search: string;
  onSearch: (v: string) => void;
  media: MediaFilter;
  onMedia: (v: MediaFilter) => void;
  sort: SortKey;
  onSort: (v: SortKey) => void;
  sortOptions?: { id: SortKey; label: string }[];
}) {
  return (
    <div className="neu flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
      <div className="neu-inset flex flex-1 items-center gap-2 px-4 py-2">
        <Icon name="search" size={15} />
        <input
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Filter your shelf…"
          aria-label="Filter your shelf"
          className="w-full bg-transparent text-sm outline-none placeholder:text-[#8a99b0]"
        />
      </div>
      <div className="flex gap-1.5" role="tablist" aria-label="Media filter">
        {(
          [
            { id: "all", label: "All" },
            { id: "movie", label: "Movies" },
            { id: "show", label: "Shows" },
          ] as const
        ).map((m) => (
          <button
            key={m.id}
            role="tab"
            aria-selected={media === m.id}
            onClick={() => onMedia(m.id)}
            className={
              media === m.id
                ? "neu-inset px-3.5 py-1.5 text-xs font-medium"
                : "px-3.5 py-1.5 text-xs text-[#5b6b84]"
            }
          >
            {m.label}
          </button>
        ))}
      </div>
      <select
        value={sort}
        onChange={(e) => onSort(e.target.value as SortKey)}
        aria-label="Sort shelf"
        className="neu-inset px-3 py-2 text-xs outline-none"
      >
        {sortOptions.map((o) => (
          <option key={o.id} value={o.id}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
