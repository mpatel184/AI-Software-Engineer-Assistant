"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUser } from "@/lib/hooks/use-auth";
import { tokenStore } from "@/lib/auth/token-store";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

/**
 * Client-side route guard for the dashboard. Redirects to /login when there is
 * no valid session. The backend remains the source of truth — every API call is
 * independently authorized — this only governs UX/navigation.
 */
export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const hasToken = typeof window !== "undefined" && Boolean(tokenStore.get());
  const { data: user, isLoading, isError } = useCurrentUser();

  useEffect(() => {
    if (!hasToken || isError) {
      router.replace("/login");
    }
  }, [hasToken, isError, router]);

  if (!hasToken || isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Skeleton className="h-32 w-80" />
      </div>
    );
  }

  if (!user) return null;
  return <>{children}</>;
}
