"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth-store";

export default function HomePage() {
  const router      = useRouter();
  const hydrated    = useAuthStore((s) => s.hydrated);
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!hydrated) return;
    router.replace(accessToken ? "/dashboard" : "/login");
  }, [hydrated, accessToken, router]);

  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}
