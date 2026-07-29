import { api } from "./client";
import type {
  Producto,
  ProductoCrearRequest,
  ProductoActualizarRequest,
  AjusteStockRequest,
  MovimientoInventario,
  Categoria,
  Sucursal,
} from "./types";

export const productosApi = {
  /**
   * Listado de productos. `sucursal_id` es OBLIGATORIO en backend
   * (si se omite devuelve [] vacío). Soporta búsqueda y modo admin.
   */
  list: (params: {
    sucursal_id:        string;
    search?:            string;
    incluir_inactivos?: boolean;
  }) => api.get<Producto[]>("/api/productos", { params }),

  get: (id: string) => api.get<Producto>(`/api/productos/${id}`),

  create: (data: ProductoCrearRequest) =>
    api.post<Producto>("/api/productos", data),

  update: (id: string, data: ProductoActualizarRequest) =>
    api.put<Producto>(`/api/productos/${id}`, data),

  /** Soft-delete: marca producto inactivo. */
  delete: (id: string) => api.delete<void>(`/api/productos/${id}`),

  /** Ajuste manual de stock + ledger. */
  ajusteStock: (productoId: string, data: AjusteStockRequest) =>
    api.post<Producto>(`/api/productos/${productoId}/ajuste-stock`, data),

  /** Historial de movimientos del producto (paginado por backend). */
  movimientos: (productoId: string) =>
    api.get<MovimientoInventario[]>(`/api/productos/${productoId}/movimientos`),
};

export const categoriasApi = {
  /** Lista categorías; backend exige `sucursal_id` para filtrar. */
  list: (params: { sucursal_id: string }) =>
    api.get<Categoria[]>("/api/categorias", { params }),

  create: (data: { nombre: string; sucursal_id: string }) =>
    api.post<Categoria>("/api/categorias", data),

  update: (id: string, data: { nombre: string }) =>
    api.put<Categoria>(`/api/categorias/${id}`, data),

  delete: (id: string) => api.delete<void>(`/api/categorias/${id}`),
};

export const sucursalesApi = {
  list: () => api.get<Sucursal[]>("/api/sucursales"),

  create: (data: { nombre: string }) =>
    api.post<Sucursal>("/api/sucursales", data),

  update: (id: string, data: { nombre?: string; activo?: boolean }) =>
    api.put<Sucursal>(`/api/sucursales/${id}`, data),
};
