"use client";

import { useCountUp } from "@/lib/motion";

/** Animated integer counter (instant under reduced motion). */
export function CountUp({ value, className }: { value: number; className?: string }) {
  const display = useCountUp(value);
  return <span className={className}>{display}</span>;
}
