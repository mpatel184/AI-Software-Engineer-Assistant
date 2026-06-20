"use client";

import { ApiError } from "@/lib/api/client";
import { analysesApi } from "@/lib/api/analyses";
import type { Analysis } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const KEY = "analyses";
const ACTIVE = new Set(["queued", "running"]);

/** Latest architecture analysis for a repo, polling while a run is active. */
export function useLatestAnalysis(repoId: string) {
  return useQuery<Analysis | null>({
    queryKey: [KEY, "latest", repoId],
    queryFn: async () => {
      try {
        return await analysesApi.latest(repoId);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
    refetchInterval: (q) =>
      q.state.data && ACTIVE.has(q.state.data.status) ? 3000 : false,
  });
}

export function useTriggerAnalysis(repoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => analysesApi.trigger(repoId),
    onSuccess: (data) => qc.setQueryData([KEY, "latest", repoId], data),
  });
}
