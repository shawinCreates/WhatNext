import type { QueryClient } from "@tanstack/react-query";

type Entry = { id: number };

/** Optimistically patch one entry in a list cache; returns a rollback. */
export function patchCached(
  queryClient: QueryClient,
  key: string[],
  id: number,
  patch: Record<string, unknown>,
) {
  const prev = queryClient.getQueryData<Entry[]>(key);
  queryClient.setQueryData<Entry[]>(key, (old) =>
    old?.map((e) => (e.id === id ? { ...e, ...patch } : e)),
  );
  return () => queryClient.setQueryData(key, prev);
}

/** Optimistically drop one entry from a list cache; returns a rollback. */
export function removeCached(
  queryClient: QueryClient,
  key: string[],
  id: number,
) {
  const prev = queryClient.getQueryData<Entry[]>(key);
  queryClient.setQueryData<Entry[]>(key, (old) =>
    old?.filter((e) => e.id !== id),
  );
  return () => queryClient.setQueryData(key, prev);
}
