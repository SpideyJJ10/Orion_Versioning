"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";
import { Toaster } from "sonner";
import { BrandingProvider } from "@/lib/branding/branding-provider";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime:        30_000,        // 30s
            gcTime:           5 * 60_000,    // 5min
            refetchOnWindowFocus: false,
            retry:            (failureCount, error: unknown) => {
              // No reintentar 401/403/404
              const status = (error as { status?: number })?.status;
              if (status && [401, 403, 404].includes(status)) return false;
              return failureCount < 2;
            },
          },
          mutations: {
            retry: 0,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <BrandingProvider>{children}</BrandingProvider>
      <Toaster
        position="top-right"
        richColors
        closeButton
        toastOptions={{
          classNames: {
            toast:       "bg-card text-card-foreground border-border",
            description: "text-muted-foreground",
          },
        }}
      />
      {process.env.NEXT_PUBLIC_DEV_TOOLS === "true" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
