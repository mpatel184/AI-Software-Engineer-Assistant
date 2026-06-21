"use client";

import { reportsApi } from "@/lib/api/reports";
import type { Report, ReportSummary, ReportType } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const KEY = "reports";

export function useReports(repoId: string) {
  return useQuery<ReportSummary[]>({
    queryKey: [KEY, repoId],
    queryFn: () => reportsApi.list(repoId),
  });
}

export function useReport(repoId: string, reportId: string | null) {
  return useQuery<Report>({
    queryKey: [KEY, "detail", reportId],
    queryFn: () => reportsApi.get(repoId, reportId as string),
    enabled: Boolean(reportId),
  });
}

export function useGenerateReport(repoId: string) {
  const qc = useQueryClient();
  return useMutation<Report, unknown, ReportType>({
    mutationFn: (type: ReportType) => reportsApi.generate(repoId, type),
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, repoId] }),
  });
}

/** Download a report's PDF, triggering a browser save. */
export async function downloadReportPdf(repoId: string, reportId: string, title: string) {
  const blob = await reportsApi.downloadPdf(repoId, reportId);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
