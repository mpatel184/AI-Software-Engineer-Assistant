import { apiClient } from "@/lib/api/client";
import type { RefactoringResult, RepoFiles } from "@/types/api";

export const refactoringApi = {
  listFiles: (repoId: string) =>
    apiClient.get<RepoFiles>(`/repositories/${repoId}/refactoring/files`),

  suggest: (repoId: string, filePath: string) =>
    apiClient.post<RefactoringResult>(`/repositories/${repoId}/refactoring`, {
      file_path: filePath,
    }),
};
