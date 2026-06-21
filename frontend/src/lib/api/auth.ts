import { apiClient } from "@/lib/api/client";
import type {
  ChangePasswordPayload,
  LoginPayload,
  RegisterPayload,
  TokenResponse,
  UpdateProfilePayload,
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

  updateProfile: (payload: UpdateProfilePayload) =>
    apiClient.patch<User>("/auth/me", payload),

  changePassword: (payload: ChangePasswordPayload) =>
    apiClient.post<void>("/auth/change-password", payload),
};
