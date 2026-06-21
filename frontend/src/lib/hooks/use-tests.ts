"use client";

import { testsApi } from "@/lib/api/tests";
import type { GeneratedTest, RepoFiles } from "@/types/api";
import { useMutation, useQuery } from "@tanstack/react-query";

export function useRepoFiles(repoId: string) {
  return useQuery<RepoFiles>({
    queryKey: ["repo-files", repoId],
    queryFn: () => testsApi.listFiles(repoId),
  });
}

export function useGenerateTests(repoId: string) {
  return useMutation<GeneratedTest, unknown, string>({
    mutationFn: (filePath: string) => testsApi.generate(repoId, filePath),
  });
}
