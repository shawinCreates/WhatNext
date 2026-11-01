"use client";

import type { EntryPatch, LibraryStatus } from "@/lib/api";
import { Icon } from "@/components/icons";

/** Circular shelf buttons in the reference pattern: add, watched toggle, favorite, remove. */
export function ShelfActions({
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
  const circle =
    "pressable flex !rounded-full p-3 disabled:opacity-50";
  if (!entry) {
    return (
      <div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => onAdd("WATCHED")}
            disabled={busy.add}
            title="Mark watched"
            aria-label="Mark watched"
            className={`neu ${circle}`}
          >
            <Icon name="check" size={17} />
          </button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>
    );
  }

  const watched = entry.status === "WATCHED";
  const rejected = entry.status === "REJECTED";
  if (rejected) {
    return (
      <div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => onUpdate({ status: "WATCHLIST" })}
            disabled={busy.update}
            title="Undo rejection"
            aria-label="Undo rejection"
            className="neu pressable px-4 py-2 text-xs font-medium disabled:opacity-50"
          >
            Undo reject
          </button>
          <button
            onClick={onRemove}
            disabled={busy.remove}
            title="Remove from shelf"
            aria-label="Remove from shelf"
            className={`neu ${circle} text-[#5b6b84] hover:text-red-600`}
          >
            <Icon name="x" size={16} />
          </button>
        </div>
        <p className="mt-2 text-xs text-[#5b6b84]">
          Rejected — hidden from recommendations.
        </p>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>
    );
  }
  return (
    <div>
      <div className="flex items-center gap-2.5">
        <button
          onClick={() => onUpdate({ status: watched ? "WATCHLIST" : "WATCHED" })}
          disabled={busy.update}
          title={watched ? "Move back to watchlist" : "Mark watched"}
          aria-label={watched ? "Watched — move back to watchlist" : "Mark watched"}
          aria-pressed={watched}
          className={watched ? `neu-inset ${circle} text-[#5457d6]` : `neu ${circle}`}
        >
          <Icon name="check" size={17} />
        </button>
        <button
          key={String(entry.is_favorite)}
          onClick={() => onUpdate({ is_favorite: !entry.is_favorite })}
          disabled={busy.update}
          aria-pressed={entry.is_favorite}
          title={entry.is_favorite ? "Remove from favorites" : "Add to favorites"}
          aria-label={entry.is_favorite ? "Remove from favorites" : "Add to favorites"}
          className={entry.is_favorite ? `neu-inset ${circle} text-[#5457d6]` : `neu ${circle}`}
        >
          <Icon name="star" size={17} filled={entry.is_favorite} className="animate-pop" />
        </button>
        <button
          onClick={() => onUpdate({ status: "REJECTED" })}
          disabled={busy.update}
          title="Not for me — hide from recommendations"
          aria-label="Not for me — hide from recommendations"
          className="neu pressable px-4 py-2 text-xs font-medium text-[#5b6b84] hover:text-red-600 disabled:opacity-50"
        >
          Not for me
        </button>
        <button
          onClick={onRemove}
          disabled={busy.remove}
          title="Remove from shelf"
          aria-label="Remove from shelf"
          className={`neu ${circle} text-[#5b6b84] hover:text-red-600`}
        >
          <Icon name="x" size={16} />
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
