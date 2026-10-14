"use client";

import Image from "next/image";
import Link from "next/link";
import { posterUrl } from "@/lib/api";
import { Icon, type IconName } from "@/components/icons";

export type ShelfItem = {
  key: string;
  title: string;
  year?: string;
  badge?: string;
  posterPath?: string | null;
  href: string;
  overlay?: {
    label: string;
    icon: IconName;
    filled?: boolean;
    tone?: "danger" | "accent";
    onPress: () => void;
    pending?: boolean;
  };
};

/** Shared poster wall for the shelf pages: cards + hover overlay action. */
export function ShelfGrid({ items, empty }: { items: ShelfItem[]; empty: string }) {
  if (items.length === 0) {
    return (
      <p className="neu-inset px-5 py-8 text-sm text-[#5b6b84]">{empty}</p>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {items.map((item, i) => {
        const poster = posterUrl(item.posterPath);
        return (
          <div
            key={item.key}
            className="neu card-lift group mount-in p-2.5 pb-3"
            style={{ animationDelay: `${Math.min(i, 10) * 40}ms` }}
          >
            <Link
              href={item.href}
              className="relative block overflow-hidden rounded-xl"
              aria-label={item.title}
            >
              <span className="relative block h-56 w-full overflow-hidden rounded-xl sm:h-64">
                {poster ? (
                  <Image
                    src={poster}
                    alt=""
                    fill
                    sizes="(max-width: 640px) 45vw, (max-width: 1024px) 30vw, 200px"
                    className="object-cover transition-transform duration-300 group-hover:scale-105"
                    loading="lazy"
                  />
                ) : (
                  <span className="neu-inset flex h-full w-full items-center justify-center p-2 text-center text-xs text-[#5b6b84]">
                    {item.title}
                  </span>
                )}
              </span>
              {item.badge && (
                <span className="neu-inset absolute top-2 left-2 px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase">
                  {item.badge}
                </span>
              )}
              {item.overlay && (
                <span
                  role="button"
                  tabIndex={0}
                  aria-label={`${item.overlay.label}: ${item.title}`}
                  onClick={(e) => {
                    e.preventDefault();
                    item.overlay!.onPress();
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      item.overlay!.onPress();
                    }
                  }}
                  className={`absolute top-2 right-2 p-1.5 !rounded-full md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 ${
                    item.overlay.tone === "danger"
                      ? "neu text-red-600"
                      : "neu-inset text-[#5457d6]"
                  }`}
                >
                  <Icon name={item.overlay.icon} size={13} filled={item.overlay.filled} />
                </span>
              )}
            </Link>
            <p className="mt-1.5 truncate text-[13px] font-medium">{item.title}</p>
            {item.year && (
              <p className="flex items-center gap-1 text-[11px] text-[#5b6b84]">
                <Icon name="calendar" size={11} />
                {item.year}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
