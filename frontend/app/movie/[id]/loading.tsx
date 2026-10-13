export default function Loading() {
  return (
    <div className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
      <div className="neu-inset px-6 py-10" aria-busy>
        <p className="text-sm text-[#5b6b84]">Loading movie…</p>
      </div>
    </div>
  );
}
