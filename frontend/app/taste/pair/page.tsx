"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, posterUrl, type PairItem, type PairComparison } from "@/lib/api";
import { go } from "@/lib/motion";
import { Icon } from "@/components/icons";

function TitleCard({ item, side }: { item: PairItem; side: "a" | "b" }) {
  const k = item.kind === "movie" ? "film" : "tv";
  const genres = (item.genres ?? []).slice(0, 3).map((g) => g.name).join(" · ");
  return (
    <article
      className="neu p-5 flex flex-col gap-3"
      aria-labelledby={`pair-${side}-title`}
    >
      <div className="flex items-center gap-2 text-xs font-semibold tracking-wide uppercase text-[#5b6b84]">
        <Icon name={k} size={13} />
        <span>{side === "a" ? "Title A" : "Title B"}</span>
      </div>
      {item.poster_path ? (
        <div className="relative aspect-video w-full overflow-hidden rounded-xl mb-2">
          <img
            src={posterUrl(item.poster_path, "w500") ?? undefined}
            alt={item.title}
            className="h-full w-full object-cover"
          />
        </div>
      ) : (
        <div className="neu-inset aspect-video w-full flex items-center justify-center rounded-xl mb-2 text-xs text-[#5b6b84]">
          No poster
        </div>
      )}
      <h3 id={`pair-${side}-title`} className="font-semibold tracking-tight leading-snug">
        {item.title}
      </h3>
      {item.year && (
        <p className="text-xs text-[#5b6b84]">{String(item.year)}</p>
      )}
      {genres && (
        <p className="text-[11px] text-[#5b6b84] leading-relaxed">{genres}</p>
      )}
    </article>
  );
}

function ComparisonRow({ c }: { c: PairComparison }) {
  const winnerLabel =
    c.winner_tkey === "tie"
      ? "Tie"
      : c.winner_tkey === "neither"
        ? "Neither"
        : c.winner_tkey === c.tkey_a
          ? "A won"
          : "B won";
  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-[#d8e0ea]/60 text-sm">
      <span className="shrink-0 font-mono text-[11px] text-[#5b6b84]">
        {c.tkey_a} vs {c.tkey_b}
      </span>
      <span className="flex-1 text-[#5b6b84]">{winnerLabel}</span>
      <span className="shrink-0 font-mono text-[11px] text-[#5b6b84]">
        {c.created_at ? new Date(c.created_at).toLocaleDateString() : ""}
      </span>
    </div>
  );
}

export default function PairwisePage() {
  const queryClient = useQueryClient();
  const pair = useQuery({
    queryKey: ["taste-pair"],
    queryFn: api.tastePair,
    retry: 1,
  });
  const history = useQuery({
    queryKey: ["taste-pairs"],
    queryFn: api.tastePairs,
  });
  const submit = useMutation({
    mutationFn: ({
      tkeyA,
      tkeyB,
      winnerTkey,
    }: {
      tkeyA: string;
      tkeyB: string;
      winnerTkey: string;
    }) => api.tastePairSubmit(tkeyA, tkeyB, winnerTkey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["taste-pair"] });
      queryClient.invalidateQueries({ queryKey: ["taste-pairs"] });
    },
  });

  const [verdict, setVerdict] = useState<"a" | "b" | "tie" | "neither" | null>(null);

  const a = pair.data?.a;
  const b = pair.data?.b;

  const handleVerdict = (v: "a" | "b" | "tie" | "neither") => {
    if (!a || !b) return;
    setVerdict(v);
    const winner =
      v === "tie"
        ? "tie"
        : v === "neither"
          ? "neither"
          : v === "a"
            ? a.tkey
            : b.tkey;
    submit.mutate({ tkeyA: a.tkey, tkeyB: b.tkey, winnerTkey: winner });
  };

  const submitting = submit.isPending;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-6 py-8">
      <header className="flex flex-col gap-2">
        <h1 className="font-display text-3xl tracking-wide">Pairwise comparisons</h1>
        <p className="text-sm text-[#5b6b84]">
          Pick the title you prefer. Each choice sharpens your taste profile.
        </p>
      </header>

      {pair.isPending ? (
        <div className="neu-inset shimmer px-6 py-16" aria-busy>
          <p className="text-sm text-[#5b6b84]">Picking a pair…</p>
        </div>
      ) : pair.isError ? (
        <p className="neu-inset px-6 py-8 text-sm text-red-600">
          {String(pair.error ?? "Unable to load a pair.")}
        </p>
      ) : a && b ? (
        <>
          <section
            aria-label="Compare two titles"
            className="flex flex-col lg:flex-row gap-6 items-start"
          >
            <TitleCard item={a} side="a" />
            <div className="flex flex-col items-center justify-center gap-3 lg:min-w-[140px]">
              <button
                type="button"
                onClick={() => handleVerdict("a")}
                disabled={submitting || verdict === "a"}
                className={`w-full !rounded-full px-6 py-3 text-sm font-semibold transition-all ${
                  verdict === "a"
                    ? "neu-inset text-[#5457d6]"
                    : "neu pressable text-[#5b6b84] hover:text-[#5457d6]"
                }`}
              >
                <Icon name="chevronLeft" size={14} /> A wins
              </button>
              <button
                type="button"
                onClick={() => handleVerdict("tie")}
                disabled={submitting || verdict === "tie"}
                className={`w-full !rounded-full px-6 py-3 text-sm font-semibold transition-all ${
                  verdict === "tie"
                    ? "neu-inset text-[#5457d6]"
                    : "neu pressable text-[#5b6b84] hover:text-[#5457d6]"
                }`}
              >
                 <Icon name="x" size={14} /> Tie
               </button>
               <button
                 type="button"
                 onClick={() => handleVerdict("neither")}
                 disabled={submitting || verdict === "neither"}
                 className={`w-full !rounded-full px-6 py-3 text-sm font-semibold transition-all ${
                   verdict === "neither"
                     ? "neu-inset text-[#5457d6]"
                     : "neu pressable text-[#5b6b84] hover:text-[#5457d6]"
                 }`}
               >
                 Neither
               </button>
              <button
                type="button"
                onClick={() => handleVerdict("b")}
                disabled={submitting || verdict === "b"}
                className={`w-full !rounded-full px-6 py-3 text-sm font-semibold transition-all ${
                  verdict === "b"
                    ? "neu-inset text-[#5457d6]"
                    : "neu pressable text-[#5b6b84] hover:text-[#5457d6]"
                }`}
              >
                B wins <Icon name="chevronRight" size={14} />
              </button>
              {submitting && (
                <p className="text-[11px] text-[#5b6b84]">Recording…</p>
              )}
            </div>
            <TitleCard item={b} side="b" />
          </section>

          {verdict !== null && !submitting && (
            <p className="text-xs font-medium text-[#5457d6]">
              Recorded. Fetching your next pair…
            </p>
          )}
          {submitting && (
            <p className="text-xs text-[#5b6b84]">Recording your choice…</p>
          )}
        </>
      ) : (
        <div className="neu-inset px-6 py-16 text-center">
          <p className="text-sm text-[#5b6b84]">
            No unseen titles left to compare. Import more from Browse.
          </p>
          <Link href="/" className="mt-4 inline-block text-sm font-medium underline">
            Browse titles
          </Link>
        </div>
      )}

      <section aria-label="Comparison history" className="border-t border-[#d8e0ea]/60 pt-6">
        <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold tracking-tight">
          <Icon name="history" size={17} /> Your comparisons
        </h2>
        {!history.data || history.data.results.length === 0 ? (
          <p className="neu-inset px-6 py-8 text-sm text-[#5b6b84]">
            No comparisons yet — make your first pick above.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-0">
            {history.data.results.map((c) => (
              <ComparisonRow key={c.id} c={c} />
            ))}
          </div>
        )}
      </section>

      <footer className="flex justify-center pb-4">
        <p className="font-mono text-xs text-[#5b6b84]">
          WhatNext · movies, shows & anime
        </p>
      </footer>
    </div>
  );
}
