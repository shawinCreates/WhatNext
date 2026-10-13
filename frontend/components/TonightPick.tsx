"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import type { HeroSlide } from "@/components/Hero";
import { Icon } from "@/components/icons";

export type TonightPick = HeroSlide & { reason: string };

/** One confident pick with a reason line and shuffle — no carousel. */
export function TonightPick({ picks }: { picks: TonightPick[] }) {
  const [index, setIndex] = useState(0);

  useEffect(() => setIndex(0), [picks.length]);
  if (picks.length === 0) return null;
  const pick = picks[Math.min(index, picks.length - 1)];

  return (
    <section className="neu overflow-hidden" aria-label="Tonight's pick" aria-live="polite">
      <div className="flex min-h-[380px] flex-col sm:flex-row">
        <div className="flex max-w-xl flex-1 flex-col justify-center gap-4 p-7 sm:p-10">
          <p className="neu-inset w-fit px-4 py-1.5 text-[11px] font-semibold tracking-[0.2em] text-[#5b6b84] uppercase">
            {pick.badge ?? "Tonight's pick"}
          </p>
          <h1 className="font-display text-3xl leading-tight tracking-wide text-balance sm:text-5xl">
            {pick.title}
          </h1>
          <p className="flex items-start gap-2 text-sm leading-relaxed text-[#5b6b84]">
            <Icon name="sparkles" size={16} />
            <span>{pick.reason}</span>
          </p>
          {pick.meta && (
            <p className="text-sm font-medium">{pick.meta}</p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-3">
            {pick.href ? (
              <Link
                href={pick.href}
                className="neu flex items-center gap-2 px-6 py-2.5 text-sm font-semibold"
              >
                <Icon name="play" size={15} filled /> Watch tonight
              </Link>
            ) : pick.onOpen ? (
              <button
                type="button"
                onClick={pick.onOpen}
                disabled={pick.opening}
                className="neu flex items-center gap-2 px-6 py-2.5 text-sm font-semibold disabled:opacity-50"
              >
                <Icon name="play" size={15} filled />
                {pick.opening ? "Opening…" : "Watch tonight"}
              </button>
            ) : null}
            {picks.length > 1 && (
              <button
                type="button"
                onClick={() => setIndex((i) => (i + 1) % picks.length)}
                className="neu flex items-center gap-2 px-5 py-2.5 text-sm text-[#5b6b84]"
                aria-label="Shuffle to another pick"
              >
                <Icon name="compass" size={15} /> Shuffle
              </button>
            )}
          </div>
        </div>
        <div className="relative min-h-56 flex-1">
          {pick.backdrop && (
            <Image
              key={pick.key}
              src={pick.backdrop}
              alt=""
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 512px"
              className="object-cover"
            />
          )}
          <div
            className="absolute inset-0 hidden sm:block"
            aria-hidden
            style={{
              background:
                "linear-gradient(100deg, var(--n-bg) 0%, transparent 45%)",
            }}
          />
        </div>
      </div>
    </section>
  );
}
