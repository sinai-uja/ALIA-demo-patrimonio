"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";

export function AuthHydrator({ children }: { children: React.ReactNode }) {
  const hydrate = useAuthStore((s) => s.hydrate);
  const hydrated = useAuthStore((s) => s.hydrated);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const isLoginPage = pathname === "/login";

  // Show neutral loading screen until hydration completes
  if (!hydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-stone-300 border-t-amber-500" />
      </div>
    );
  }

  // Redirect unauthenticated users to login
  if (!isAuthenticated && !isLoginPage) {
    router.replace("/login");
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-stone-300 border-t-amber-500" />
      </div>
    );
  }

  return <>{children}</>;
}
