"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type ThemeMode = "system" | "light" | "dark";

interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
}

/**
 * Tema preferido del usuario. Persistido en localStorage como
 * `orion-theme`. El bootstrap inline en `<head>` lo lee antes de
 * hidratar React para evitar el flash de tema incorrecto.
 */
export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      mode: "system",
      setMode: (mode) => set({ mode }),
    }),
    {
      name: "orion-theme",
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? window.localStorage : (undefined as unknown as Storage)
      ),
    }
  )
);

/**
 * Resuelve el tema efectivo (light|dark) considerando preferencia del SO.
 * Sólo usar en client components.
 */
export function resolveTheme(mode: ThemeMode): "light" | "dark" {
  if (mode !== "system") return mode;
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
