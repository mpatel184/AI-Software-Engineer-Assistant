import { apiClient } from "@/lib/api/client";
import { tokenStore } from "@/lib/auth/token-store";
import type { CreateRepoPayload, Page, Repository, RepoStatus } from "@/types/api";

export interface ListReposParams {
  page?: number;
  page_size?: number;
  status_filter?: RepoStatus;
  search?: string;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

export const repositoriesApi = {
  list: (params: ListReposParams = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    if (params.status_filter) qs.set("status_filter", params.status_filter);
    if (params.search) qs.set("search", params.search);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return apiClient.get<Page<Repository>>(`/repositories${suffix}`);
  },

  get: (id: string) => apiClient.get<Repository>(`/repositories/${id}`),

  createFromGitHub: (payload: CreateRepoPayload) =>
    apiClient.post<Repository>("/repositories", payload),

  reindex: (id: string) => apiClient.post<Repository>(`/repositories/${id}/reindex`),

  remove: (id: string) => apiClient.delete<void>(`/repositories/${id}`),

  /** Upload uses multipart, so it bypasses the JSON apiClient. */
  upload: async (name: string, file: File): Promise<Repository> => {
    const form = new FormData();
    form.append("name", name);
    form.append("file", file);

    const token = tokenStore.get();
    const res = await fetch(`${BASE_URL}/repositories/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
      credentials: "include",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.detail || "Upload failed");
    return data as Repository;
  },
};
