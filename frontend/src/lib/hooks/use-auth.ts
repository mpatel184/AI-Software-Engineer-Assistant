"use client";

import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { tokenStore } from "@/lib/auth/token-store";
import type { LoginPayload, RegisterPayload, TokenResponse, User } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export const CURRENT_USER_KEY = ["auth", "me"] as const;

/** Loads the authenticated user. `enabled` only when an access token exists. */
export function useCurrentUser() {
  return useQuery<User>({
    queryKey: CURRENT_USER_KEY,
    queryFn: authApi.me,
    enabled: typeof window !== "undefined" && Boolean(tokenStore.get()),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: LoginPayload) => authApi.login(payload),
    onSuccess: (data: TokenResponse) => {
      tokenStore.set(data.access_token);
      qc.setQueryData(CURRENT_USER_KEY, data.user);
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (payload: RegisterPayload) => authApi.register(payload),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: () => {
      tokenStore.clear();
      qc.removeQueries({ queryKey: CURRENT_USER_KEY });
      qc.clear();
    },
  });
}

/** Type guard for surfacing API error messages in forms. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}
