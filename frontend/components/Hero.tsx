"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Icon } from "@/components/icons";

export type HeroSlide = {
  key: string;
  title: string;
  meta?: string;
  overview?: string;
  backdrop?: string | null;
  badge?: string;
  href?: string;
  onOpen?: () => void;
  opening?: boolean;
};

const AUTOPLAY_MS = 6000;

export function Hero({ slides }: { slides: HeroSlide[] }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const go = useCallback(
    (dir: number) =>
      setIndex((i) => (i + dir + slides.length) % slides.length),
    [slides.length],
  );

  useEffect(() => {
    if (paused || slides.length < 2) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    timer.current = setInterval(() => go(1), AUTOPLAY_MS);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [paused, slides.length, go]);

  useEffect(() => setIndex(0), [slides.length]);

  if (slides.length === 0) return null;
  const slide = slides[Math.min(index, slides.length - 1)];

  return (
    <section
      className="neu overflow-hidden"
      aria-label="Featured titles"
      aria-roledescription="carousel"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div className="relative min-h-[440px] sm:min-h-[560px]">
        {slides.map((item, i) => (
          <div
            key={item.key}
            aria-hidden={i !== index}
            className={`absolute inset-0 transition-opacity duration-700 ${i === index ? "opacity-100" : "pointer-events-none opacity-0"}`}
          >
            {item.backdrop && (
              <Image
                src={item.backdrop}
                alt=""
                fill
                priority={i === 0}
                sizes="(max-width: 1024px) 100vw, 1024px"
                className={`object-cover ${i === index ? "kenburns" : ""}`}
              />
            )}
          </div>
        ))}
        <div className="hero-scrim absolute inset-0" aria-hidden />
        <div
          key={slide.key}
          className="relative flex h-full min-h-[440px] max-w-2xl flex-col justify-end gap-4 p-7 pb-24 sm:min-h-[560px] sm:p-12 sm:pb-28"
        >
          {slide.badge && (
            <p className="neu-inset w-fit px-4 py-1.5 text-[11px] font-semibold tracking-[0.2em] text-[#5b6b84] uppercase">
              {slide.badge}
            </p>
          )}
          <h1 className="font-display text-3xl leading-tight tracking-wide text-balance sm:text-5xl">
            {slide.title}
          </h1>
          {slide.meta && (
            <p className="text-sm font-medium text-[#5b6b84]">{slide.meta}</p>
          )}
          {slide.overview && (
            <p className="line-clamp-3 max-w-lg text-sm leading-relaxed">
              {slide.overview}
            </p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-3">
            {slide.href ? (
              <Link
                href={slide.href}
                className="neu flex items-center gap-2 px-6 py-2.5 text-sm font-semibold"
              >
                <Icon name="play" size={15} filled /> More info
              </Link>
            ) : slide.onOpen ? (
              <button
                type="button"
                onClick={slide.onOpen}
                disabled={slide.opening}
                className="neu flex items-center gap-2 px-6 py-2.5 text-sm font-semibold disabled:opacity-50"
              >
                <Icon name="play" size={15} filled />
                {slide.opening ? "Opening…" : "More info"}
              </button>
            ) : null}
          </div>
        </div>
        <div className="hero-scrim-bottom absolute inset-x-0 bottom-0 h-20" aria-hidden />

        {slides.length > 1 && (
          <div className="absolute right-5 bottom-5 left-5 flex items-center justify-between sm:right-8 sm:left-8">
            <p className="font-display text-xs tracking-[0.25em] text-[#5b6b84]" aria-live="polite">
              {String(index + 1).padStart(2, "0")} / {String(slides.length).padStart(2, "0")}
            </p>
            <div className="flex items-center gap-2">
              <div className="mr-2 hidden gap-1.5 sm:flex" role="tablist" aria-label="Featured slides">
                {slides.map((item, i) => (
                  <button
                    key={item.key}
                    role="tab"
                    aria-selected={i === index}
                    aria-label={`Show ${item.title}`}
                    onClick={() => setIndex(i)}
                    className={`h-2 rounded-full transition-all ${i === index ? "neu-inset w-8" : "neu w-2"}`}
                  />
                ))}
              </div>
              <button
                type="button"
                onClick={() => go(-1)}
                aria-label="Previous featured"
                className="neu p-2"
              >
                <Icon name="chevronLeft" size={16} />
              </button>
              <button
                type="button"
                onClick={() => go(1)}
                aria-label="Next featured"
                className="neu p-2"
              >
                <Icon name="chevronRight" size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
