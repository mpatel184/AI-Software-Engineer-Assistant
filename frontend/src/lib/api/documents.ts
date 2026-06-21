import { apiClient } from "@/lib/api/client";
import type { Document, DocumentSummary, DocumentType } from "@/types/api";

export const documentsApi = {
  generate: (repoId: string, type: DocumentType) =>
    apiClient.post<Document>(`/repositories/${repoId}/documents`, { type }),

  list: (repoId: string) =>
    apiClient.get<DocumentSummary[]>(`/repositories/${repoId}/documents`),

  get: (repoId: string, documentId: string) =>
    apiClient.get<Document>(`/repositories/${repoId}/documents/${documentId}`),
};
