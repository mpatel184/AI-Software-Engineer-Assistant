import { apiClient } from "@/lib/api/client";
import type { Analysis, AnalysisType } from "@/types/api";

export const analysesApi = {
  trigger: (repoId: string, type: AnalysisType = "architecture") =>
    apiClient.post<Analysis>(`/repositories/${repoId}/analyses`, { type }),

  latest: (repoId: string, type: AnalysisType = "architecture") =>
    apiClient.get<Analysis>(`/repositories/${repoId}/analyses/latest?type=${type}`),

  list: (repoId: string) => apiClient.get<Analysis[]>(`/repositories/${repoId}/analyses`),
};
