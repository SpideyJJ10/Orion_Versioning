import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: {
    default:  "Orion",
    template: "%s — Orion",
  },
  description: "Tu negocio en digital — Orion Tech",
  applicationName: "Orion",
  manifest:        "/manifest.json",
  icons: {
    icon: [
      { url: "/orion-logo-mark.png", type: "image/png" },
    ],
    shortcut: "/orion-logo-mark.png",
    apple:    "/orion-logo-mark.png",
  },
  openGraph: {
    type:        "website",
    siteName:    "Orion",
    title:       "Orion",
    description: "Tu negocio en digital",
    images:      [{ url: "/orion-logo.png", width: 512, height: 512, alt: "Orion" }],
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)",  color: "#0a0512" },
  ],
  width:        "device-width",
  initialScale: 1,
  // Permitimos zoom para accesibilidad (no fijamos maximumScale).
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // El script inline previene flash de tema incorrecto: aplica `dark` antes
  // de hidratar React si el usuario lo eligió (o si el SO lo prefiere).
  const themeBootstrap = `
    (function(){
      try {
        var s = localStorage.getItem('orion-theme');
        var mode = s ? JSON.parse(s).state.mode : 'system';
        var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        var resolved = mode === 'system' ? (prefersDark ? 'dark' : 'light') : mode;
        if (resolved === 'dark') document.documentElement.classList.add('dark');
      } catch (_) {}
    })();
  `;

  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
      </head>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
