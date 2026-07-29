import { api } from "./client";
import type { Orden, OrdenListItem, CrearOrdenRequest, ReciboData } from "./types";

export const ordenesApi = {
  /** Lista órdenes (resumen). Backend acepta sucursal_id, fecha (YYYY-MM-DD), tz_offset. */
  list: (params?: {
    sucursal_id?: string;
    fecha?:       string;
    tz_offset?:   number;
    incluir_anuladas?: boolean;
  }) => api.get<OrdenListItem[]>("/api/ordenes", { params }),

  /** Detalle completo de una orden con sus items. */
  get: (id: string) => api.get<Orden>(`/api/ordenes/${id}`),

  /** Crea orden + descuenta stock atómicamente. */
  create: (data: CrearOrdenRequest) => api.post<Orden>("/api/ordenes", data),

  /** Datos de recibo listos para imprimir (incluye negocio + pago). */
  recibo: (id: string) => api.get<ReciboData>(`/api/ordenes/${id}/recibo`),

  /**
   * Anula la orden (soft-delete) y RESTAURA el stock vendido.
   * Requiere PIN de administrador.
   */
  anular: (id: string, pin: string) =>
    api.delete<void>(`/api/ordenes/${id}`, { params: { pin } }),
};
