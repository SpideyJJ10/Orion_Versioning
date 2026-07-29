import { api } from "./client";
import type {
  AlertaStock,
  InventarioSummary,
  MovimientoInventario,
} from "./types";

export const inventarioApi = {
  summary: (sucursalId?: string) =>
    api.get<InventarioSummary>("/api/inventario/summary", {
      params: sucursalId ? { sucursal_id: sucursalId } : undefined,
    }),

  alertas: (sucursalId?: string) =>
    api.get<AlertaStock[]>("/api/inventario/alertas", {
      params: sucursalId ? { sucursal_id: sucursalId } : undefined,
    }),

  movimientos: (params?: {
    sucursal_id?: string;
    producto_id?: string;
    tipo?:        "entrada" | "salida";
    desde?:       string;
    hasta?:       string;
    limit?:       number;
  }) => api.get<MovimientoInventario[]>("/api/inventario/movimientos", { params }),
};
