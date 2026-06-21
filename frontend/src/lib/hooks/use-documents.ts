"use client";

import { documentsApi } from "@/lib/api/documents";
import type { Document, DocumentSummary, DocumentType } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const KEY = "documents";
const ACTIVE = new Set(["queued", "running"]);

/** All documents for a repo. Polls while any document is still generating. */
export function useDocuments(repoId: string) {
  return useQuery<DocumentSummary[]>({
    queryKey: [KEY, "list", repoId],
    queryFn: () => documentsApi.list(repoId),
    refetchInterval: (q) =>
      (q.state.data ?? []).some((d) => ACTIVE.has(d.status)) ? 3000 : false,
  });
}

/** Full document (with content), polling while it is still generating. */
export function useDocument(repoId: string, documentId: string | null) {
  return useQuery<Document>({
    queryKey: [KEY, "detail", documentId],
    queryFn: () => documentsApi.get(repoId, documentId as string),
    enabled: Boolean(documentId),
    refetchInterval: (q) => (q.state.data && ACTIVE.has(q.state.data.status) ? 3000 : false),
  });
}

export function useGenerateDocument(repoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (type: DocumentType) => documentsApi.generate(repoId, type),
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "list", repoId] }),
  });
}
