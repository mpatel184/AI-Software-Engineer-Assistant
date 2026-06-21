import { apiClient } from "@/lib/api/client";
import type { ChatMessage } from "@/types/api";

export const chatApi = {
  ask: (repoId: string, question: string) =>
    apiClient.post<ChatMessage>(`/repositories/${repoId}/chat`, { question }),

  history: (repoId: string) =>
    apiClient.get<ChatMessage[]>(`/repositories/${repoId}/chat`),

  clear: (repoId: string) => apiClient.delete<void>(`/repositories/${repoId}/chat`),
};
