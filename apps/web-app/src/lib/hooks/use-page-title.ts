"use client";

import { useEffect } from "react";
import { useBrandingStore } from "@/lib/stores/branding-store";

export function usePageTitle(sectionName: string) {
  const branding = useBrandingStore((s) => s.branding);
  const businessName = branding?.nombre_comercial || "Orion OS";

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.title = `${sectionName} | ${businessName}`;
    }
  }, [sectionName, businessName]);
}
