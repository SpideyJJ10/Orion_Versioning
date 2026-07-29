"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { UsuarioPublico, Rol } from "@/lib/api/types";

interface AuthState {
  accessToken:  string | null;
  refreshToken: string | null;
  user:         UsuarioPublico | null;
  hydrated:     boolean;

  setTokens:  (access: string, refresh: string) => void;
  setUser:    (user: UsuarioPublico) => void;
  setSession: (access: string, refresh: string, user: UsuarioPublico) => void;
  logout:     () => void;
  setHydrated: () => void;

  isAuthenticated: () => boolean;
  hasRole:         (...roles: Rol[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken:  null,
      refreshToken: null,
      user:         null,
      hydrated:     false,

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),

      setUser: (user) => set({ user }),

      setSession: (access, refresh, user) =>
        set({ accessToken: access, refreshToken: refresh, user }),

      logout: () => {
        set({ accessToken: null, refreshToken: null, user: null });
        // Redirect manual: el guard del layout se encarga.
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
      },

      setHydrated: () => set({ hydrated: true }),

      isAuthenticated: () => !!get().accessToken && !!get().user,

      hasRole: (...roles) => {
        const u = get().user;
        return !!u && roles.includes(u.rol);
      },
    }),
    {
      name:    "orion-auth",
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? window.localStorage : (undefined as unknown as Storage)
      ),
      partialize: (state) => ({
        accessToken:  state.accessToken,
        refreshToken: state.refreshToken,
        user:         state.user,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated();
      },
    }
  )
);
