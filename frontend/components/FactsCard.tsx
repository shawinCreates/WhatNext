"use client";

import { Icon, type IconName } from "@/components/icons";

/** Key-value facts card in the reference's exact pattern, neu skin. */
export function FactsCard({
  facts,
}: {
  facts: { icon: IconName; label: string; value: string }[];
}) {
  if (facts.length === 0) return null;
  return (
    <aside className="neu overflow-hidden" aria-label="Facts">
      <ul className="divide-y divide-[#c8d0db]">
        {facts.map((fact) => (
          <li key={fact.label} className="flex items-center justify-between gap-3 px-4 py-2.5">
            <span className="flex items-center gap-2 text-xs text-[#5b6b84]">
              <Icon name={fact.icon} size={14} />
              {fact.label}
            </span>
            <span className="truncate text-xs font-medium">{fact.value}</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
