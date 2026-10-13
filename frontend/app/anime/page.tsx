import { Suspense } from "react";
import { MediaHub } from "@/components/MediaHub";

export default function AnimePage() {
  return (
    <Suspense>
      <MediaHub
        kind="anime"
        heading="Anime"
        subheading="Japanese animation, from classics to simulcasts"
      />
    </Suspense>
  );
}
