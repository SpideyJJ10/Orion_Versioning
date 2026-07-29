"use client";
/**
 * Next.js App Router global error boundary.
 *
 * Required by Sentry to capture React render errors in the App Router.
 * Without this file, unhandled React rendering errors are not reported.
 *
 * Docs: https://nextjs.org/docs/app/api-reference/file-conventions/error#global-errorjs
 */
import * as Sentry from "@sentry/nextjs";
import NextError from "next/error";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
      Sentry.captureException(error);
    }
  }, [error]);

  return (
    <html lang="es">
      <body>
        {/* Delegate to Next.js default error page UI */}
        <NextError statusCode={0} />
        <button
          onClick={reset}
          style={{ position: "fixed", bottom: 16, right: 16, padding: "8px 16px" }}
        >
          Reintentar
        </button>
      </body>
    </html>
  );
}
