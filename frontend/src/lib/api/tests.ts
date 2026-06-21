import { apiClient } from "@/lib/api/client";
import type { GeneratedTest, RepoFiles } from "@/types/api";

export const testsApi = {
  listFiles: (repoId: string) =>
    apiClient.get<RepoFiles>(`/repositories/${repoId}/tests/files`),

  generate: (repoId: string, filePath: string) =>
    apiClient.post<GeneratedTest>(`/repositories/${repoId}/tests`, { file_path: filePath }),
};
