"use client";

import { chatApi } from "@/lib/api/chat";
import type { ChatMessage } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const KEY = "chat";

export function useChatHistory(repoId: string) {
  return useQuery<ChatMessage[]>({
    queryKey: [KEY, repoId],
    queryFn: () => chatApi.history(repoId),
  });
}

export function useAskQuestion(repoId: string) {
  const qc = useQueryClient();
  return useMutation<ChatMessage, unknown, string>({
    mutationFn: (question: string) => chatApi.ask(repoId, question),
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, repoId] }),
  });
}

export function useClearChat(repoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => chatApi.clear(repoId),
    onSuccess: () => qc.setQueryData([KEY, repoId], []),
  });
}
