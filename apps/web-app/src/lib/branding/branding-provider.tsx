"use client";

import { useEffect } from "react";
import { useBrandingStore } from "@/lib/stores/branding-store";
import { useThemeStore, resolveTheme } from "@/lib/stores/theme-store";
import { hslFromHex } from "@/lib/formatters";

/**
 * Aplica el branding del tenant + tema preferido al DOM:
 *  - `--primary` y `--ring` se setean a partir de `color_primary` del branding.
 *  - `--accent` y `--accent-foreground` siguen `color_accent`.
 *  - El modo `light/dark` se resuelve combinando preferencia explícita del
 *    usuario (`useThemeStore`) y, si está en "system", el `prefers-color-scheme`.
 *  - Si el branding define un `tema` específico (override del owner), gana.
 *  - Reacciona en vivo a cambios del SO (mediaQuery listener).
 *  - Setea el título dinámico con el `nombre_comercial` del tenant.
 */
export function BrandingProvider({ children }: { children: React.ReactNode }) {
  const branding = useBrandingStore((s) => s.branding);
  const mode     = useThemeStore((s) => s.mode);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const root = document.documentElement;

    // ── Colores primarios (sobrescriben tokens shadcn) ─────────────
    if (branding?.color_primary) {
      root.style.setProperty("--primary", hslFromHex(branding.color_primary));
      root.style.setProperty("--ring",    hslFromHex(branding.color_primary));
    }
    if (branding?.color_accent) {
      root.style.setProperty("--accent", hslFromHex(branding.color_accent));
    }

    // ── Resolución de tema ──────────────────────────────────────────
    // El override de branding ("warm" se trata como "light" cálido) tiene
    // prioridad sobre la preferencia del usuario (clásico white-label).
    const applyTheme = () => {
      let isDark: boolean;
      if (branding?.tema === "dark")      isDark = true;
      else if (branding?.tema === "light" || branding?.tema === "warm") isDark = false;
      else                                isDark = resolveTheme(mode) === "dark";
      root.classList.toggle("dark", isDark);
    };
    applyTheme();

    // Listener para cambios del SO en modo "system".
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => applyTheme();
    mq.addEventListener("change", handler);

    // ── Título dinámico ────────────────────────────────────────────
    if (branding?.nombre_comercial) {
      const baseTitle = document.title.includes("—")
        ? document.title.split("—")[0].trim()
        : document.title || "Orion";
      document.title = `${baseTitle} — ${branding.nombre_comercial}`;
    }

    return () => mq.removeEventListener("change", handler);
  }, [branding, mode]);

  return <>{children}</>;
}
