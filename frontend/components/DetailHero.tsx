"use client";

import type { ReactNode } from "react";
import Image from "next/image";
import { backdropUrl } from "@/lib/api";
import { useParallax } from "@/lib/motion";
import { Icon } from "@/components/icons";
import { FactsCard } from "@/components/FactsCard";
import type { IconName } from "@/components/icons";

/** Reference-style title block in neu skin: genre line, actions, meta, creator, synopsis, facts. */
export function DetailHero({
  title,
  backdropPath,
  kicker,
  genres,
  overview,
  metaYear,
  metaBadge,
  vote,
  creator,
  facts,
  onTrailer,
  trailerLabel = "Trailer",
  shelf,
}: {
  title: string;
  backdropPath?: string | null;
  kicker?: string;
  genres: { id: number; name: string }[];
  overview?: string;
  metaYear?: string;
  metaBadge?: string;
  vote?: string;
  creator?: { label: string; value: string };
  facts: { icon: IconName; label: string; value: string }[];
  onTrailer?: () => void;
  trailerLabel?: string;
  shelf: ReactNode;
}) {
  const backdrop = backdropUrl(backdropPath);
  const parallax = useParallax<HTMLDivElement>(0.12);

  return (
    <section aria-label={title} className="relative">
      <div className="neu relative z-10 overflow-hidden">
        <div
          className="relative h-[52vh] min-h-[340px] overflow-hidden lg:h-[68vh]"
          style={{
            maskImage: "linear-gradient(to bottom, black 55%, transparent 99%)",
            WebkitMaskImage: "linear-gradient(to bottom, black 55%, transparent 99%)",
          }}
        >
          {backdrop && (
            <div ref={parallax} className="absolute inset-0 will-change-transform">
              <Image
                src={backdrop}
                alt=""
                fill
                priority
                sizes="(max-width: 1024px) 100vw, 1024px"
                className="object-cover object-top"
              />
            </div>
          )}
          <div className="hero-scrim absolute inset-0" aria-hidden />
          <div className="hero-scrim-bottom absolute inset-x-0 bottom-0 h-24" aria-hidden />
        </div>

        <div className="relative -mt-40 flex flex-col px-6 pb-8 lg:-mt-72 lg:flex-row lg:items-start lg:justify-between lg:gap-10 lg:px-10">
          <div className="flex w-full max-w-[700px] flex-col items-center text-center lg:max-w-[650px] lg:items-start lg:text-left">
            {kicker && (
              <p className="mb-3 flex w-fit items-center gap-1.5 rounded-full bg-[#5457d6]/10 px-3 py-1 text-[11px] font-semibold tracking-wide text-[#5457d6] uppercase">
                <Icon name="trophy" size={12} /> {kicker}
              </p>
            )}
            <h1 className="font-display text-3xl leading-tight tracking-wide text-balance sm:text-5xl">
              {title}
            </h1>

            {genres.length > 0 && (
              <p className="mt-3 text-sm font-medium lg:text-base">
                {genres.map((g, i) => (
                  <span key={g.id}>
                    {g.name}
                    {i < genres.length - 1 && (
                      <span className="mx-2 text-[#a3b1c6]" aria-hidden>•</span>
                    )}
                  </span>
                ))}
              </p>
            )}

            <div className="mt-5 flex items-center gap-3">
              {onTrailer && (
                <button
                  type="button"
                  onClick={onTrailer}
                  className="neu pressable flex items-center gap-2 !rounded-full px-6 py-3 text-sm font-semibold"
                >
                  <Icon name="play" size={16} filled /> {trailerLabel}
                </button>
              )}
              {shelf}
            </div>

            {(metaYear || metaBadge || vote) && (
              <p className="mt-5 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-sm font-medium lg:justify-start lg:text-base">
                {metaYear && <span>{metaYear}</span>}
                {metaBadge && (
                  <span className="neu-inset px-2 py-0.5 text-xs lg:text-sm">{metaBadge}</span>
                )}
                {vote && (
                  <span className="flex items-center gap-1">
                    <Icon name="star" size={14} filled className="text-[#b98a1d]" />
                    {vote}
                  </span>
                )}
              </p>
            )}

            {creator && (
              <p className="mt-1.5 w-full text-sm text-[#5b6b84] lg:text-base">
                {creator.label}: <span className="font-medium text-[#2d3a4f]">{creator.value}</span>
              </p>
            )}

            {overview && (
              <p className="mt-4 line-clamp-3 w-full text-sm leading-relaxed lg:text-base">
                {overview}
              </p>
            )}

            {facts.length > 0 && (
              <div className="mt-6 w-full lg:hidden">
                <FactsCard facts={facts} />
              </div>
            )}
          </div>

          {facts.length > 0 && (
            <div className="hidden w-[280px] shrink-0 lg:block">
              <FactsCard facts={facts} />
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
