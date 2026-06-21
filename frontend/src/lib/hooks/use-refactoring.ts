"use client";

import { refactoringApi } from "@/lib/api/refactoring";
import type { RefactoringResult, RepoFiles } from "@/types/api";
import { useMutation, useQuery } from "@tanstack/react-query";

export function useRefactoringFiles(repoId: string) {
  return useQuery<RepoFiles>({
    queryKey: ["refactoring-files", repoId],
    queryFn: () => refactoringApi.listFiles(repoId),
  });
}

export function useSuggestRefactorings(repoId: string) {
  return useMutation<RefactoringResult, unknown, string>({
    mutationFn: (filePath: string) => refactoringApi.suggest(repoId, filePath),
  });
}
