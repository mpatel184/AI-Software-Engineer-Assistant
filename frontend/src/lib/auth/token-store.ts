"use client";

/**
 * Access-token storage. The access token is short-lived and kept in memory +
 * localStorage mirror so a page refresh can rehydrate. The refresh token is
 * held in an httpOnly cookie by the backend and never touched by JS.
 */
const ACCESS_KEY = "ai_swe_access_token";

let inMemoryToken: string | null = null;

export const tokenStore = {
  get(): string | null {
    if (inMemoryToken) return inMemoryToken;
    if (typeof window === "undefined") return null;
    inMemoryToken = window.localStorage.getItem(ACCESS_KEY);
    return inMemoryToken;
  },
  set(token: string): void {
    inMemoryToken = token;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ACCESS_KEY, token);
    }
  },
  clear(): void {
    inMemoryToken = null;
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(ACCESS_KEY);
    }
  },
};
