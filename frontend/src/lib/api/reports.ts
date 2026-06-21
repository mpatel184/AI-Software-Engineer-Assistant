import { apiClient, ApiError } from "@/lib/api/client";
import { tokenStore } from "@/lib/auth/token-store";
import type { Report, ReportSummary, ReportType } from "@/types/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

export const reportsApi = {
  generate: (repoId: string, type: ReportType) =>
    apiClient.post<Report>(`/repositories/${repoId}/reports`, { type }),

  list: (repoId: string) =>
    apiClient.get<ReportSummary[]>(`/repositories/${repoId}/reports`),

  get: (repoId: string, reportId: string) =>
    apiClient.get<Report>(`/repositories/${repoId}/reports/${reportId}`),

  /** Fetch the PDF as a Blob with the auth header attached. */
  downloadPdf: async (repoId: string, reportId: string): Promise<Blob> => {
    const token = tokenStore.get();
    const res = await fetch(
      `${BASE_URL}/repositories/${repoId}/reports/${reportId}/pdf`,
      {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: "include",
      },
    );
    if (!res.ok) {
      throw new ApiError({
        type: "about:blank",
        title: "error",
        status: res.status,
        detail: "Failed to download PDF.",
      });
    }
    return res.blob();
  },
};
