import { Suspense } from "react";
import { MediaHub } from "@/components/MediaHub";

export default function MoviesPage() {
  return (
    <Suspense>
      <MediaHub
        kind="movie"
        heading="Movies"
        subheading="Trending, acclaimed, and everything by genre"
      />
    </Suspense>
  );
}
