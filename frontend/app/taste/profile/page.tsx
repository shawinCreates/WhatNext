"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, type FeedbackStats, type TasteFeature } from "@/lib/api";
import { CountUp } from "@/components/CountUp";
import { Icon } from "@/components/icons";

function FeatureCard({ item, max }: { item: TasteFeature; max: number }) {
  return (
    <article className="neu p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="font-semibold tracking-tight">{item.label}</h3>
        <span
          className={`shrink-0 px-2.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase ${
            item.strength === "strong"
              ? "rounded-full bg-[#5457d6]/10 text-[#5457d6]"
              : "neu-inset text-[#5b6b84]"
          }`}
        >
          {item.strength} · {item.evidence} titles
        </span>
      </div>
      <p className="mt-1 text-sm text-[#5b6b84]">{item.description}</p>
      <div
        className="neu-inset mt-3 h-2 overflow-hidden"
        role="img"
        aria-label={`Weight ${item.weight.toFixed(1)}`}
      >
        <div
          className="h-full rounded-full bg-[#5457d6]/70"
          style={{ width: `${max > 0 ? (Math.abs(item.weight) / max) * 100 : 0}%` }}
        />
      </div>
      {item.titles.length > 0 && (
        <p className="mt-2.5 truncate text-xs text-[#5b6b84]">
          {item.titles
            .map((t) => `${t.title}${t.rating != null ? ` ★${t.rating}` : ""}`)
            .join(" · ")}
        </p>
      )}
    </article>
  );
}

function RecoFunnelCard({ stats }: { stats: FeedbackStats }) {
  return (
    <section aria-label="Recommendation funnel" className="neu p-5">
      <h2 className="flex items-center gap-2 text-lg font-semibold tracking-tight">
        <Icon name="sparkles" size={17} /> What served picks did
      </h2>
      <div className="mt-3 grid grid-cols-3 gap-4 text-center">
        <div className="neu-inset px-3 py-3">
          <CountUp value={stats.served} className="font-display text-2xl" />
          <p className="mt-1 text-xs text-[#5b6b84]">suggestions shown</p>
        </div>
        <div className="neu-inset px-3 py-3">
          <CountUp value={stats.watched} className="font-display text-2xl" />
          <p className="mt-1 text-xs text-[#5b6b84]">you watched</p>
        </div>
        <div className="neu-inset px-3 py-3">
          <CountUp value={stats.rejected} className="font-display text-2xl" />
          <p className="mt-1 text-xs text-[#5b6b84]">you turned down</p>
        </div>
      </div>
      <p className="mt-3 text-sm text-[#5b6b84]">
        {stats.conversion != null
          ? `${stats.served > 0 ? Math.round((stats.conversion || 0) * 100) : 0}% of served picks made it to your shelf.`
          : "No suggestions served yet — open Tonight to start the funnel."}
      </p>
    </section>
  );
}

export default function TasteProfilePage() {
  const profile = useQuery({ queryKey: ["taste-profile"], queryFn: api.tasteProfile });
  const feedback = useQuery({ queryKey: ["reco-feedback"], queryFn: api.recoFeedback });
  const max =
    Math.max(
      0,
      ...[...(profile.data?.positive ?? []), ...(profile.data?.negative ?? [])].map(
        (f) => Math.abs(f.weight),
      ),
    ) || 1;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-6 py-8">
      <header>
        <h1 className="font-display text-3xl tracking-wide">Taste profile</h1>
        <p className="mt-1 text-sm text-[#5b6b84]">
          Learned from your ratings — plain words, no algorithms.
        </p>
      </header>

      {profile.isPending ? (
        <div className="neu-inset shimmer px-6 py-12" aria-busy>
          <p className="text-sm text-[#5b6b84]">Reading your taste…</p>
        </div>
      ) : profile.isError || !profile.data ? (
        <p className="neu-inset px-6 py-8 text-sm text-red-600">
          {String(profile.error ?? "Profile unavailable.")}
        </p>
      ) : (
        <>
          {feedback.data && <RecoFunnelCard stats={feedback.data} />}

          <section aria-label="What you respond to">
            <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold tracking-tight">
              <Icon name="flame" size={17} /> What you respond to
            </h2>
            {profile.data.positive.length === 0 ? (
              <p className="neu-inset px-6 py-8 text-sm text-[#5b6b84]">
                Rate a few titles first — your profile builds here.
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {profile.data.positive.map((item) => (
                  <FeatureCard key={item.feature} item={item} max={max} />
                ))}
              </div>
            )}
          </section>

          <section aria-label="What pushes you away">
            <h2 className="mb-3 text-lg font-semibold tracking-tight">What pushes you away</h2>
            {profile.data.negative.length === 0 ? (
              <p className="neu-inset px-6 py-8 text-sm text-[#5b6b84]">
                No dislikes recorded yet — low ratings (below 7) teach the
                model what to avoid.{" "}
                <Link href="/" className="font-medium underline">
                  Browse titles
                </Link>
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {profile.data.negative.map((item) => (
                  <FeatureCard key={item.feature} item={item} max={max} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
