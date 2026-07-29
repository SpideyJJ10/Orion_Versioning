// Sentry — client-side configuration.
//
// Loaded automatically by `@sentry/nextjs` for every browser-side bundle.
// Becomes a NO-OP when `NEXT_PUBLIC_SENTRY_DSN` is empty — safe to keep in
// repo even on environments without Sentry.
//
// Docs: https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

const DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (DSN) {
  Sentry.init({
    dsn: DSN,
    environment: process.env.NEXT_PUBLIC_VERCEL_ENV ?? process.env.NODE_ENV,
    release:     process.env.NEXT_PUBLIC_SENTRY_RELEASE,

    // Performance monitoring
    tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES ?? "0.1"),

    // Session Replay — only sample errored sessions to stay inside the free tier.
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 1.0,

    integrations: [
      Sentry.replayIntegration({
        maskAllText:    true,
        blockAllMedia:  true,
      }),
    ],

    // Don't ship PII unless we explicitly opt in.
    sendDefaultPii: false,

    // Ignore noisy framework errors that aren't actionable.
    ignoreErrors: [
      "ResizeObserver loop limit exceeded",
      "ResizeObserver loop completed with undelivered notifications",
      "Non-Error promise rejection captured",
    ],
  });
}
