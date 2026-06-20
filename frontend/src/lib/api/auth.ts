import { apiClient } from "@/lib/api/client";
import type {
  LoginPayload,
  RegisterPayload,
  TokenResponse,
  User,
} from "@/types/api";

export const authApi = {
  register: (payload: RegisterPayload) =>
    apiClient.post<User>("/auth/register", payload, { anonymous: true }),

  login: (payload: LoginPayload) =>
    apiClient.post<TokenResponse>("/auth/login", payload, { anonymous: true }),

  refresh: () => apiClient.post<TokenResponse>("/auth/refresh", undefined, { anonymous: true }),

  logout: () => apiClient.post<void>("/auth/logout"),

  me: () => apiClient.get<User>("/auth/me"),
};
