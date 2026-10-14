"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/icons";

/** Cinematic trailer dialog: letterbox bars ease in around the player. */
export function TrailerModal({
  title,
  videoName,
  videoKey,
  onClose,
}: {
  title: string;
  videoName: string;
  videoKey: string;
  onClose: () => void;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setOpen(true));
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal
      aria-label={`Trailer for ${title}`}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#2d3a4f]/60 p-4"
    >
      <div
        className="neu modal-in w-full max-w-3xl overflow-hidden p-3"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-2 flex items-center justify-between px-1">
          <p className="truncate text-sm font-medium">{videoName}</p>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close trailer"
            className="neu pressable p-1.5"
          >
            <Icon name="x" size={15} />
          </button>
        </div>
        <div className="overflow-hidden rounded-xl bg-black">
          <div className={`letterbox bg-black ${open ? "h-5 sm:h-7" : "h-0"}`} aria-hidden />
          <div className="aspect-video w-full">
            <iframe
              src={`https://www.youtube.com/embed/${videoKey}?autoplay=1&rel=0`}
              title={videoName}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              className="h-full w-full"
            />
          </div>
          <div className={`letterbox bg-black ${open ? "h-5 sm:h-7" : "h-0"}`} aria-hidden />
        </div>
      </div>
    </div>
  );
}
