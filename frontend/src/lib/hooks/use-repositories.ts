"use client";

import { repositoriesApi, type ListReposParams } from "@/lib/api/repositories";
import type { Repository } from "@/types/api";
import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";

const KEY = "repositories";

/** Statuses that mean work is in progress → poll for updates. */
const ACTIVE_STATUSES = new Set(["pending", "cloning", "indexing"]);

export function useRepositories(params: ListReposParams) {
  return useQuery({
    queryKey: [KEY, params],
    queryFn: () => repositoriesApi.list(params),
    placeholderData: keepPreviousData,
    // Poll while any repository in the page is still processing.
    refetchInterval: (query) => {
      const data = query.state.data;
      const anyActive = data?.items.some((r) => ACTIVE_STATUSES.has(r.status));
      return anyActive ? 4000 : false;
    },
  });
}

export function useRepository(id: string) {
  return useQuery({
    queryKey: [KEY, "detail", id],
    queryFn: () => repositoriesApi.get(id),
    refetchInterval: (query) =>
      query.state.data && ACTIVE_STATUSES.has(query.state.data.status) ? 4000 : false,
  });
}

export function useCreateRepository() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: repositoriesApi.createFromGitHub,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

export function useUploadRepository() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, file }: { name: string; file: File }) =>
      repositoriesApi.upload(name, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

export function useReindexRepository() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => repositoriesApi.reindex(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

export function useDeleteRepository() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => repositoriesApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

export function isProcessing(repo: Repository): boolean {
  return ACTIVE_STATUSES.has(repo.status);
}
