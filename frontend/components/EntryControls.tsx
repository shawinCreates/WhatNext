"use client";

import type { EntryPatch, LibraryStatus } from "@/lib/api";
import { Icon } from "@/components/icons";

const STATUSES: LibraryStatus[] = ["WATCHLIST", "WATCHED", "REJECTED", "SKIPPED"];

/** Slim shelf controls: status, favorite, remove. Rating/notes cut. */
export function EntryControls({
  entry,
  onAdd,
  onUpdate,
  onRemove,
  busy,
  error,
}: {
  entry: { status: LibraryStatus; is_favorite: boolean } | null;
  onAdd: (status: LibraryStatus) => void;
  onUpdate: (patch: EntryPatch) => void;
  onRemove: () => void;
  busy: { add: boolean; update: boolean; remove: boolean };
  error: string | null;
}) {
  return (
    <section className="neu p-6" aria-label="Your shelf">
      <h2 className="text-sm font-semibold tracking-wide uppercase">Your shelf</h2>
      {!entry ? (
        <div className="mt-3 flex flex-wrap gap-3">
          <button
            onClick={() => onAdd("WATCHLIST")}
            disabled={busy.add}
            className="neu flex items-center gap-2 px-5 py-2 text-sm font-medium disabled:opacity-50"
          >
            <Icon name="plus" size={15} /> Watchlist
          </button>
          <button
            onClick={() => onAdd("WATCHED")}
            disabled={busy.add}
            className="neu flex items-center gap-2 px-5 py-2 text-sm disabled:opacity-50"
          >
            <Icon name="check" size={15} /> Watched
          </button>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <select
            value={entry.status}
            onChange={(event) => onUpdate({ status: event.target.value as LibraryStatus })}
            disabled={busy.update}
            className="neu-inset px-3 py-2 text-sm outline-none disabled:opacity-50"
            aria-label="Shelf status"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button
            onClick={() => onUpdate({ is_favorite: !entry.is_favorite })}
            disabled={busy.update}
            aria-pressed={entry.is_favorite}
            title={entry.is_favorite ? "Remove from favorites" : "Add to favorites"}
            className={
              entry.is_favorite
                ? "neu-inset flex items-center gap-1.5 px-3 py-2 text-sm text-[#5457d6] disabled:opacity-50"
                : "neu flex items-center gap-1.5 px-3 py-2 text-sm disabled:opacity-50"
            }
          >
            <Icon name="star" size={15} filled={entry.is_favorite} />
            Favorite
          </button>
          <button
            onClick={onRemove}
            disabled={busy.remove}
            className="ml-auto flex items-center gap-1 text-xs text-[#5b6b84] hover:text-red-600 disabled:opacity-50"
          >
            <Icon name="x" size={13} /> Remove
          </button>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </section>
  );
}
