"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon, LogoMark, type IconName } from "@/components/icons";
import { QuickSearch } from "@/components/QuickSearch";

const LINKS: { href: string; label: string; icon: IconName }[] = [
  { href: "/", label: "Home", icon: "home" },
  { href: "/tonight", label: "Tonight", icon: "compass" },
  { href: "/movies", label: "Movies", icon: "film" },
  { href: "/shows", label: "Shows", icon: "tv" },
  { href: "/anime", label: "Anime", icon: "sparkles" },
  { href: "/watched", label: "Watched", icon: "history" },
  { href: "/favorites", label: "Favorites", icon: "star" },
  { href: "/taste/profile", label: "Taste", icon: "bookmark" },
];

function NavLinks({ pathname, centered = false }: { pathname: string; centered?: boolean }) {
  return (
    <>
      {LINKS.map((link) => {
        const active =
          link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            title={link.label}
            className={
              active
                ? "neu-inset flex flex-shrink-0 items-center gap-1.5 px-3 py-1.5 text-[13px] font-medium"
                : "flex flex-shrink-0 items-center gap-1.5 px-3 py-1.5 text-[13px] text-[#5b6b84] hover:text-[#2d3a4f]"
            }
          >
            <Icon name={link.icon} size={15} />
            <span className={centered ? "hidden xl:inline" : "hidden lg:inline"}>
              {link.label}
            </span>
          </Link>
        );
      })}
    </>
  );
}

export function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [term, setTerm] = useState("");
  const [debounced, setDebounced] = useState("");
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(term.trim()), 300);
    return () => clearTimeout(t);
  }, [term]);

  useEffect(() => {
    setOpen(false);
    setTerm("");
  }, [pathname]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let last = window.scrollY;
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;
        const y = window.scrollY;
        setHidden(y > 160 && y > last);
        last = y;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const search = (
    <div className="relative flex-shrink-0">
      <div
        className={
          open
            ? "neu-inset flex items-center gap-2 !rounded-full px-3 py-1.5"
            : "flex items-center"
        }
      >
        {open && (
          <input
            autoFocus
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            placeholder="Titles, shows, anime…"
            aria-label="Search titles"
            className="w-36 bg-transparent text-sm outline-none sm:w-48"
          />
        )}
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? "Close search" : "Open search"}
          aria-expanded={open}
          className={open ? "" : "neu flex p-2 !rounded-full"}
        >
          <Icon name={open ? "x" : "search"} size={16} />
        </button>
      </div>

      {open && <QuickSearch query={debounced} />}
    </div>
  );

  return (
    <header className="sticky top-0 z-40 px-4 pt-4 sm:px-6">
      <nav
        aria-label="Primary"
        className={`neu nav-bar mx-auto w-full max-w-6xl !rounded-3xl px-3 py-2 sm:px-5 md:!rounded-full ${hidden && !open ? "nav-hide" : ""}`}
      >
        <div className="relative flex items-center justify-between gap-2">
          <Link href="/" className="flex flex-shrink-0 items-center gap-2" aria-label="WhatNext home">
            <LogoMark />
            <span className="font-display text-sm tracking-wide sm:text-base">
              WhatNext
            </span>
          </Link>

          <div className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 md:flex">
            <NavLinks pathname={pathname} centered />
          </div>

          {search}
        </div>

        <div className="no-scrollbar mt-1 flex items-center justify-start gap-1 overflow-x-auto pb-1 sm:justify-center md:hidden">
          <NavLinks pathname={pathname} />
        </div>
      </nav>
    </header>
  );
}
