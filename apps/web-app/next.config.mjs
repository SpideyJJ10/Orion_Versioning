/** @type {import('next').NextConfig} */
let API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
if (!API_URL.startsWith("http://") && !API_URL.startsWith("https://")) {
  API_URL = `https://${API_URL}`;
}

const config = {
  reactStrictMode: true,

  // Proxear llamadas de /api al backend FastAPI
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_URL}/api/:path*`,
      },
    ];
  },



  // Headers de seguridad globales
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },

  experimental: {
    optimizePackageImports: ["lucide-react", "@radix-ui/react-icons"],
  },

  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
      { protocol: "http", hostname: "**" },
    ],
  },
};

// ─── Sentry & Serwist wrappers ──────────────────────────────────────────────
async function loadConfig() {
  let finalConfig = config;

  try {
    const withSerwistInit = (await import("@serwist/next")).default;
    const withSerwist = withSerwistInit({
      swSrc: "src/app/sw.ts",
      swDest: "public/sw.js",
      disable: false, // Habilitado en dev para que se pueda testear Offline-First
    });
    finalConfig = withSerwist(finalConfig);
  } catch (e) {
    console.log("Serwist no disponible", e);
  }

  try {
    const { withSentryConfig } = await import("@sentry/nextjs");
    return withSentryConfig(finalConfig, {
      silent: true,
      org:     process.env.SENTRY_ORG,
      project: process.env.SENTRY_PROJECT,
      sourcemaps: { disable: !process.env.SENTRY_AUTH_TOKEN },
      hideSourceMaps: true,
      disableLogger: true,
      tunnelRoute: "/monitoring",
    });
  } catch {
    return finalConfig;
  }
}

export default await loadConfig();
