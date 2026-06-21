"use client";

import { ApiError } from "@/lib/api/client";
import { analysesApi } from "@/lib/api/analyses";
import type { Analysis, AnalysisType } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const KEY = "analyses";
const ACTIVE = new Set(["queued", "running"]);

/**
 * Latest analysis of a given type for a repo, polling while a run is active.
 * Defaults to the architecture analysis used by the Analysis page.
 */
export function useLatestAnalysis(repoId: string, type: AnalysisType = "architecture") {
  return useQuery<Analysis | null>({
    queryKey: [KEY, "latest", repoId, type],
    queryFn: async () => {
      try {
        return await analysesApi.latest(repoId, type);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
    refetchInterval: (q) =>
      q.state.data && ACTIVE.has(q.state.data.status) ? 3000 : false,
  });
}

export function useTriggerAnalysis(repoId: string, type: AnalysisType = "architecture") {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => analysesApi.trigger(repoId, type),
    onSuccess: (data) => qc.setQueryData([KEY, "latest", repoId, type], data),
  });
}
