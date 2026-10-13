import type { SVGProps } from "react";

export type IconName =
  | "search"
  | "plus"
  | "check"
  | "star"
  | "chevronLeft"
  | "chevronRight"
  | "arrowLeft"
  | "play"
  | "film"
  | "tv"
  | "sparkles"
  | "flame"
  | "trophy"
  | "clock"
  | "calendar"
  | "home"
  | "bookmark"
  | "history"
  | "x"
  | "compass";

const PATHS: Record<IconName, React.ReactNode> = {
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.8-3.8" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  check: <path d="m4.5 12.5 5 5 10-11" />,
  star: <path d="m12 3 2.7 5.6 6.1.8-4.5 4.2 1.1 6-5.4-3-5.4 3 1.1-6L3.2 9.4l6.1-.8L12 3Z" />,
  chevronLeft: <path d="m14.5 5.5-7 6.5 7 6.5" />,
  chevronRight: <path d="m9.5 5.5 7 6.5-7 6.5" />,
  arrowLeft: <path d="M19 12H5m6-7-7 7 7 7" />,
  play: <path d="M8 5.5v13l11-6.5-11-6.5Z" />,
  film: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2.5" />
      <path d="M7.5 5v14M16.5 5v14M3 10h4.5M3 14h4.5M16.5 10H21M16.5 14H21" />
    </>
  ),
  tv: (
    <>
      <rect x="3" y="7" width="18" height="12" rx="2.5" />
      <path d="m9 3 3 4 3-4M9 21h6" />
    </>
  ),
  sparkles: (
    <>
      <path d="M12 4v5M12 15v5M4 12h5M15 12h5M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" />
    </>
  ),
  flame: (
    <path d="M12 3s5.5 4.5 5.5 9.5a5.5 5.5 0 0 1-11 0c0-2 1-3.8 2.3-5.2.4 1.2 1.2 2.2 2.2 2.7C11 7.5 11 5 12 3Z" />
  ),
  trophy: (
    <>
      <path d="M8 4h8v5a4 4 0 0 1-8 0V4Z" />
      <path d="M8 5H4.5a3.5 3.5 0 0 0 3.6 3.5M16 5h3.5a3.5 3.5 0 0 1-3.6 3.5M12 13v4m-4 4h8m-8 0 .8-4h6.4l.8 4" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  calendar: (
    <>
      <rect x="4" y="6" width="16" height="14" rx="2.5" />
      <path d="M4 10.5h16M8.5 3.5V7M15.5 3.5V7" />
    </>
  ),
  home: <path d="m4 11 8-7 8 7v8a1.5 1.5 0 0 1-1.5 1.5H5.5A1.5 1.5 0 0 1 4 19v-8Z" />,
  bookmark: <path d="M7 4h10v16l-5-3.5L7 20V4Z" />,
  history: (
    <>
      <path d="M4.5 12a7.5 7.5 0 1 1 2.2 5.3M4.5 12H3m1.5 0V9.5M12 8v4.5l3 1.5" />
    </>
  ),
  x: <path d="m6 6 12 12M18 6 6 18" />,
  compass: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m15.5 8.5-2 5-5 2 2-5 5-2Z" />
    </>
  ),
};

export function Icon({
  name,
  size = 16,
  filled = false,
  ...props
}: SVGProps<SVGSVGElement> & {
  name: IconName;
  size?: number;
  filled?: boolean;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      {PATHS[name]}
    </svg>
  );
}

export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <path
        d="M4 7.5 10 24l6-11 6 11 6-16.5"
        fill="none"
        stroke="currentColor"
        strokeWidth={3.2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M14.5 9.5v9l7.5-4.5-7.5-4.5Z" fill="#5457d6" />
    </svg>
  );
}
