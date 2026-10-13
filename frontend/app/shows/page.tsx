import { Suspense } from "react";
import { MediaHub } from "@/components/MediaHub";

export default function ShowsPage() {
  return (
    <Suspense>
      <MediaHub
        kind="show"
        heading="TV Shows"
        subheading="Series worth your evenings"
      />
    </Suspense>
  );
}
