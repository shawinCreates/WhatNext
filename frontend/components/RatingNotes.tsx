"use client";

import { useEffect, useState } from "react";
import type { EntryPatch } from "@/lib/api";
import { Icon } from "@/components/icons";

/** Personal 1.0–10.0 rating + note, wired to the library entry update mutation. */
export function RatingNotes({
  entry,
  onUpdate,
  busy,
  error,
}: {
  entry: { rating: number | null; personal_note: string } | null;
  onUpdate: (patch: EntryPatch) => void;
  busy: boolean;
  error: string | null;
}) {
  const [draft, setDraft] = useState(entry?.personal_note ?? "");
  const [ratingText, setRatingText] = useState(
    entry?.rating != null ? String(entry.rating) : "",
  );
  useEffect(() => setDraft(entry?.personal_note ?? ""), [entry?.personal_note]);
  useEffect(
    () => setRatingText(entry?.rating != null ? String(entry.rating) : ""),
    [entry?.rating],
  );

  if (!entry) {
    return (
      <p className="text-sm text-[#5b6b84]">
        Add this title to your shelf to rate it and keep notes.
      </p>
    );
  }

  const dirty = draft !== (entry.personal_note ?? "");
  const save = () => {
    if (dirty && !busy) onUpdate({ personal_note: draft.trim() });
  };
  // Commit typed rating: clamp 1–10, round to one decimal.
  const commitRating = () => {
    if (busy) return;
    const parsed = parseFloat(ratingText);
    if (Number.isNaN(parsed)) {
      setRatingText(entry.rating != null ? String(entry.rating) : "");
      return;
    }
    const rounded = Math.round(Math.min(10, Math.max(1, parsed)) * 10) / 10;
    setRatingText(String(rounded));
    if (rounded !== entry.rating) onUpdate({ rating: rounded });
  };
  const fill = entry.rating != null ? `${(entry.rating / 10) * 100}%` : "0%";

  return (
    <section aria-label="Your rating and notes" className="flex flex-col gap-4">
      <div>
        <p className="mb-2 text-sm font-semibold">Your rating</p>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative inline-flex" role="group" aria-label="Set rating">
            <div className="flex gap-1">
              {Array.from({ length: 10 }, (_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => entry.rating !== i + 1 && onUpdate({ rating: i + 1 })}
                  disabled={busy}
                  aria-label={`Rate ${i + 1} out of 10`}
                  aria-pressed={entry.rating === i + 1}
                  title={`${i + 1}/10`}
                  className="pressable text-[#a3b1c6] hover:text-[#b98a1d] disabled:opacity-50"
                >
                  <Icon name="star" size={20} />
                </button>
              ))}
            </div>
            <div
              className="pointer-events-none absolute inset-y-0 left-0 overflow-hidden"
              style={{ width: fill }}
              aria-hidden
            >
              <div className="flex w-max gap-1 text-[#b98a1d]">
                {Array.from({ length: 10 }, (_, i) => (
                  <Icon key={i} name="star" size={20} filled />
                ))}
              </div>
            </div>
          </div>
          <input
            type="number"
            min={1}
            max={10}
            step={0.1}
            value={ratingText}
            onChange={(e) => setRatingText(e.target.value)}
            onBlur={commitRating}
            onKeyDown={(e) => {
              if (e.key === "Enter") (e.target as HTMLInputElement).blur();
            }}
            disabled={busy}
            aria-label="Rating from 1 to 10"
            placeholder="–"
            className="neu-inset w-20 px-2.5 py-1.5 text-sm outline-none disabled:opacity-50"
          />
          {entry.rating != null && (
            <button
              type="button"
              onClick={() => {
                setRatingText("");
                onUpdate({ rating: null });
              }}
              disabled={busy}
              className="pressable text-xs font-medium text-[#5b6b84] hover:text-red-600 disabled:opacity-50"
            >
              Clear
            </button>
          )}
        </div>
        <p className="mt-1 text-xs text-[#5b6b84]">
          Click a star for a whole number, or type a decimal like 9.6.
        </p>
      </div>

      <div>
        <label htmlFor="personal-note" className="mb-2 block text-sm font-semibold">
          Your notes
        </label>
        <textarea
          id="personal-note"
          value={draft}
          onChange={(e) => setDraft(e.target.value.slice(0, 2000))}
          onBlur={save}
          disabled={busy}
          rows={3}
          placeholder="What worked, what didn't, who'd like this…"
          className="neu-inset w-full resize-y px-4 py-3 text-sm outline-none placeholder:text-[#a3b1c6] disabled:opacity-50"
        />
        <div className="mt-1.5 flex items-center justify-between gap-3">
          <p className="text-xs text-[#5b6b84]">{draft.length}/2000</p>
          {dirty && (
            <button
              type="button"
              onClick={save}
              disabled={busy}
              className="neu pressable px-4 py-1.5 text-xs font-semibold disabled:opacity-50"
            >
              Save note
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
    </section>
  );
}
