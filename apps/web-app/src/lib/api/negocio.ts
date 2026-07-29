import { api } from "./client";

export const negocioApi = {
  getMetodosPago: () => {
    return api.get<string[]>("/api/v3/negocio/metodos-pago");
  },
  updateMetodosPago: (metodos_pago: string[]) => {
    return api.post<string[]>("/api/v3/negocio/metodos-pago", { metodos_pago });
  },
};
