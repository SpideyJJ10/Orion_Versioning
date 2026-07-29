/**
 * Next.js instrumentation hook.
 *
 * Replaces the legacy `sentry.server.config.ts` and `sentry.edge.config.ts`
 * files for Next.js 14+ App Router. Sentry is initialised here so it can
 * correctly intercept server-side exceptions and edge-runtime errors.
 *
 * Docs: https://nextjs.org/docs/app/building-your-application/optimizing/instrumentation
 */
export async function register() {
  const DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!DSN) return; // No-op when Sentry is not configured

  if (process.env.NEXT_RUNTIME === "nodejs") {
    // Server-side (Node.js runtime)
    const Sentry = await import("@sentry/nextjs");
    Sentry.init({
      dsn: DSN,
      environment: process.env.VERCEL_ENV ?? process.env.NODE_ENV,
      release:     process.env.SENTRY_RELEASE ?? process.env.NEXT_PUBLIC_SENTRY_RELEASE,
      tracesSampleRate: Number(process.env.SENTRY_TRACES ?? "0.1"),
      sendDefaultPii: false,
    });
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    // Edge runtime (middleware, edge route handlers)
    const Sentry = await import("@sentry/nextjs");
    Sentry.init({
      dsn: DSN,
      environment: process.env.VERCEL_ENV ?? process.env.NODE_ENV,
      release:     process.env.SENTRY_RELEASE ?? process.env.NEXT_PUBLIC_SENTRY_RELEASE,
      tracesSampleRate: Number(process.env.SENTRY_TRACES ?? "0.1"),
      sendDefaultPii: false,
    });
  }
}
