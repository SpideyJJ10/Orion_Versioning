"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { Branding } from "@/lib/api/types";

interface BrandingState {
  branding: Branding | null;
  setBranding: (b: Branding | null) => void;
}

export const useBrandingStore = create<BrandingState>()(
  persist(
    (set) => ({
      branding: null,
      setBranding: (branding) => set({ branding }),
    }),
    {
      name:    "orion-branding",
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? window.localStorage : (undefined as unknown as Storage)
      ),
    }
  )
);
