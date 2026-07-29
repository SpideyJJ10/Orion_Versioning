import { api } from "./client";
import type { Branding, BrandingUpdateRequest } from "./types";

export const brandingApi = {
  /** Branding del tenant autenticado. */
  get: () => api.get<Branding>("/api/v3/branding"),

  /** Actualiza colores/tema/logo/categorías default. */
  update: (data: BrandingUpdateRequest) =>
    api.put<Branding>("/api/v3/branding", data),
};
