"use client";

import { useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { posterUrl } from "@/lib/api";
import { useInView } from "@/lib/motion";
import { Icon, type IconName } from "@/components/icons";

export type RailItem = {
  key: string;
  title: string;
  year?: string;
  tag?: string;
  posterPath?: string | null;
  href?: string;
  onSelect?: () => void;
  selectPending?: boolean;
};

export function Row({
  title,
  subtitle,
  icon,
  items,
  empty,
  numbered = false,
  viewAllHref,
  hoverPlay = false,
}: {
  title: string;
  subtitle?: string;
  icon?: IconName;
  items: RailItem[];
  empty?: string;
  numbered?: boolean;
  viewAllHref?: string;
  hoverPlay?: boolean;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const scrollBy = (dir: number) =>
    scroller.current?.scrollBy({ left: dir * 560, behavior: "smooth" });
  const { ref: revealRef, visible } = useInView<HTMLElement>();

  return (
    <section
      ref={revealRef}
      aria-label={title}
      className={`reveal ${visible ? "visible" : ""}`}
    >
      <div className="mb-3 flex items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          {icon && (
            <span className="neu flex p-2.5" aria-hidden>
              <Icon name={icon} size={18} />
            </span>
          )}
          <div>
            <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
            {subtitle && <p className="text-xs text-[#5b6b84]">{subtitle}</p>}
          </div>
        </div>
        {(items.length > 3 || viewAllHref) && (
          <div className="flex items-center gap-2">
            {viewAllHref && (
              <Link
                href={viewAllHref}
                className="mr-1 flex items-center gap-1 text-xs font-medium text-[#5b6b84] hover:text-[#2d3a4f]"
              >
                View all <Icon name="chevronRight" size={13} />
              </Link>
            )}
            {items.length > 3 && (
              <>
                <button
                  type="button"
                  onClick={() => scrollBy(-1)}
                  aria-label={`Scroll ${title} back`}
                  className="neu pressable p-2"
                >
                  <Icon name="chevronLeft" size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => scrollBy(1)}
                  aria-label={`Scroll ${title} forward`}
                  className="neu pressable p-2"
                >
                  <Icon name="chevronRight" size={16} />
                </button>
              </>
            )}
          </div>
        )}
      </div>
      {items.length === 0 ? (
        <p className="neu-inset px-5 py-6 text-sm text-[#5b6b84]">
          {empty ?? "Nothing here yet."}
        </p>
      ) : (
        <div
          ref={scroller}
          className="no-scrollbar -mx-1 flex gap-5 overflow-x-auto px-1 pt-2 pb-4"
        >
          {items.map((item, i) => {
            const poster = posterUrl(item.posterPath, "w342");
            const clickable = Boolean(item.href || item.onSelect);
            const visual = (
              <>
                <div className="relative h-60 w-full flex-shrink-0 overflow-hidden rounded-xl">
                  {poster ? (
                    <Image
                      src={poster}
                      alt={item.title}
                      fill
                      sizes="176px"
                      className="object-cover transition-transform duration-300 hover:scale-105"
                      loading="lazy"
                    />
                  ) : (
                    <div className="neu-inset flex h-full w-full items-center justify-center p-3 text-center">
                      <Icon name="film" size={22} />
                    </div>
                  )}
                  {hoverPlay && clickable && poster && (
                    <span
                      aria-hidden
                      className="absolute inset-0 hidden items-center justify-center bg-[#2d3a4f]/35 opacity-0 transition-opacity duration-300 group-hover:opacity-100 sm:flex"
                    >
                      <span className="neu flex !rounded-full p-3.5">
                        <Icon name="play" size={20} filled />
                      </span>
                    </span>
                  )}
                </div>
                <p className="truncate text-[13px] font-medium">{item.title}</p>
                {item.tag && (
                  <p className="flex items-center gap-1 truncate text-[11px] font-medium text-[#5457d6]">
                    <Icon name="trophy" size={11} />
                    {item.tag}
                  </p>
                )}
                {item.year && (
                  <p className="flex items-center gap-1 text-[11px] text-[#5b6b84]">
                    <Icon name="calendar" size={11} />
                    {item.year}
                  </p>
                )}
              </>
            );
            const body = item.href ? (
              <Link
                href={item.href}
                className="group flex flex-col gap-1.5 rounded-md focus-visible:outline-2 focus-visible:outline-offset-2"
                aria-label={item.title}
              >
                {visual}
              </Link>
            ) : item.onSelect ? (
              <button
                type="button"
                onClick={item.onSelect}
                disabled={item.selectPending}
                className="group flex w-full flex-col gap-1.5 rounded-md text-left disabled:opacity-60"
                aria-label={`View ${item.title}`}
              >
                {visual}
              </button>
            ) : (
              <div className="flex flex-col gap-1.5">{visual}</div>
            );
            return (
              <div
                key={item.key}
                className={`reveal flex flex-shrink-0 items-stretch ${visible ? "visible" : ""}`}
                style={{ transitionDelay: `${Math.min(i, 8) * 45}ms` }}
              >
                {numbered && (
                  <span
                    aria-hidden
                    className="font-display -mr-3 mb-1 self-end text-6xl leading-none text-[#a3b1c6] select-none"
                  >
                    {i + 1}
                  </span>
                )}
                <div className="neu card-lift w-44 flex-shrink-0 p-2.5 pb-3">
                  {body}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
