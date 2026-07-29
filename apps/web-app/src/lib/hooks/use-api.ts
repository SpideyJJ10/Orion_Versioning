"use client";

import { db } from "@/lib/db";
import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import {
  authApi,
  usuariosApi,
  productosApi,
  categoriasApi,
  sucursalesApi,
  ordenesApi,
  mlApi,
  brandingApi,
  reportesApi,
  inventarioApi,
  mesasApi,
  type ApiError,
  type CrearOrdenRequest,
  type CrearUsuarioRequest,
  type AjusteStockRequest,
  type ProductoCrearRequest,
  type ProductoActualizarRequest,
  type BrandingUpdateRequest,
  type AlertaSeveridad,
  type AlertaTipo,
} from "@/lib/api";

const handleError = (error: unknown, defaultMessage: string) => {
  const apiError = error as ApiError;
  const message  = apiError?.message || defaultMessage;
  toast.error(message);
};

/** ─── AUTH ─────────────────────────────────────────────── */
export function useMe() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn:  () => authApi.me(),
    staleTime: 5 * 60_000,
  });
}

/** ─── PRODUCTOS ────────────────────────────────────────── */
export function useProductos(params: Parameters<typeof productosApi.list>[0] | undefined) {
  return useQuery({
    queryKey: ["productos", params],
    queryFn: async () => {
      try {
        const data = await productosApi.list(params!);
        if (typeof window !== "undefined") {
          db.products.clear().then(() => {
            db.products.bulkAdd(data.map(p => ({
              id: p.id,
              nombre: p.nombre,
              precio: p.precio,
              stock: p.stock,
              stock_minimo: p.stock_minimo,
              categoria: p.categoria,
              sucursal_id: p.sucursal_id,
              activo: p.activo
            })));
          });
        }
        return data;
      } catch (error) {
        console.warn("[Offline] Failed to fetch products from API, falling back to local DB:", error);
        if (typeof window !== "undefined") {
          const localData = await db.products
            .where("sucursal_id")
            .equals(params?.sucursal_id || "")
            .toArray();
          if (localData.length > 0) {
            return localData as any[];
          }
        }
        throw error;
      }
    },
    enabled:  !!params?.sucursal_id,
    staleTime: 5 * 60_000, // 5 minutos
  });
}

export function useProducto(id: string | undefined) {
  return useQuery({
    queryKey: ["productos", id],
    queryFn:  () => productosApi.get(id!),
    enabled:  !!id,
  });
}

export function useCrearProducto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProductoCrearRequest) => productosApi.create(data),
    onSuccess:  () => {
      qc.invalidateQueries({ queryKey: ["productos"] });
      qc.invalidateQueries({ queryKey: ["inventario"] });
      toast.success("Producto creado");
    },
    onError: (e) => handleError(e, "Error al crear producto"),
  });
}

export function useActualizarProducto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: string; data: ProductoActualizarRequest }) =>
      productosApi.update(input.id, input.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["productos"] });
      toast.success("Producto actualizado");
    },
    onError: (e) => handleError(e, "Error al actualizar producto"),
  });
}

export function useEliminarProducto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => productosApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["productos"] });
      toast.success("Producto eliminado");
    },
    onError: (e) => handleError(e, "Error al eliminar producto"),
  });
}

export function useAjusteStock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { productoId: string; data: AjusteStockRequest }) =>
      productosApi.ajusteStock(input.productoId, input.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["productos"] });
      qc.invalidateQueries({ queryKey: ["inventario"] });
      toast.success("Stock ajustado");
    },
    onError: (e) => handleError(e, "Error al ajustar stock"),
  });
}

/** ─── CATEGORÍAS / SUCURSALES ────────────────────── */
export function useCategorias(sucursalId: string | undefined) {
  return useQuery({
    queryKey: ["categorias", sucursalId],
    queryFn: async () => {
      try {
        const data = await categoriasApi.list({ sucursal_id: sucursalId! });
        if (typeof window !== "undefined") {
          db.categories.clear().then(() => {
            db.categories.bulkAdd(data.map(c => ({
              id: c.id,
              nombre: c.nombre,
              activo: c.activo,
              sucursal_id: c.sucursal_id
            })));
          });
        }
        return data;
      } catch (error) {
        console.warn("[Offline] Failed to fetch categories from API, falling back to local DB:", error);
        if (typeof window !== "undefined") {
          const localData = await db.categories
            .where("sucursal_id")
            .equals(sucursalId || "")
            .toArray();
          if (localData.length > 0) {
            return localData as any[];
          }
        }
        throw error;
      }
    },
    enabled:  !!sucursalId,
    staleTime: 5 * 60_000, // 5 minutos
  });
}

export function useSucursales() {
  return useQuery({
    queryKey: ["sucursales"],
    queryFn: async () => {
      try {
        const data = await sucursalesApi.list();
        if (typeof window !== "undefined") {
          db.sucursales.clear().then(() => {
            db.sucursales.bulkAdd(data.map(s => ({
              id: s.id,
              nombre: s.nombre,
              activo: s.activo
            })));
          });
        }
        return data;
      } catch (error) {
        console.warn("[Offline] Failed to fetch sucursales from API, falling back to local DB:", error);
        if (typeof window !== "undefined") {
          const localData = await db.sucursales.toArray();
          if (localData.length > 0) {
            return localData as any[];
          }
        }
        throw error;
      }
    },
    staleTime: 10 * 60_000, // 10 minutos
  });
}

/** ─── ÓRDENES ──────────────────────────────────────────── */
export function useOrdenes(params?: Parameters<typeof ordenesApi.list>[0]) {
  return useQuery({
    queryKey: ["ordenes", params],
    queryFn:  () => ordenesApi.list(params),
  });
}

export function useCrearOrden() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CrearOrdenRequest) => ordenesApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ordenes"] });
      qc.invalidateQueries({ queryKey: ["productos"] });
      qc.invalidateQueries({ queryKey: ["reportes"] });
      qc.invalidateQueries({ queryKey: ["inventario"] });
      toast.success("Venta registrada");
    },
    onError: (e) => handleError(e, "Error al registrar venta"),
  });
}

export function useAnularOrden() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: string; pin: string }) =>
      ordenesApi.anular(input.id, input.pin),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ordenes"] });
      qc.invalidateQueries({ queryKey: ["productos"] });
      qc.invalidateQueries({ queryKey: ["reportes"] });
      qc.invalidateQueries({ queryKey: ["inventario"] });
      toast.success("Orden anulada — stock restaurado");
    },
    onError: (e) => handleError(e, "Error al anular orden"),
  });
}

/** Trae datos del recibo (negocio + pago + items) listos para imprimir. */
export function useReciboOrden(id: string | undefined) {
  return useQuery({
    queryKey: ["ordenes", id, "recibo"],
    queryFn:  () => ordenesApi.recibo(id!),
    enabled:  !!id,
  });
}

/** ─── INVENTARIO ───────────────────────────────────────── */
export function useInventarioSummary(sucursalId?: string) {
  return useQuery({
    queryKey: ["inventario", "summary", sucursalId],
    queryFn:  () => inventarioApi.summary(sucursalId),
  });
}

export function useInventarioAlertas(sucursalId?: string) {
  return useQuery({
    queryKey: ["inventario", "alertas", sucursalId],
    queryFn:  () => inventarioApi.alertas(sucursalId),
  });
}

export function useMovimientosInventario(
  params?: Parameters<typeof inventarioApi.movimientos>[0]
) {
  return useQuery({
    queryKey: ["inventario", "movimientos", params],
    queryFn:  () => inventarioApi.movimientos(params),
  });
}

/** ─── REPORTES ─────────────────────────────────── */
export function useReporteDiario(params?: Parameters<typeof reportesApi.diario>[0]) {
  return useQuery({
    queryKey: ["reportes", "diario", params],
    queryFn:  () => reportesApi.diario(params),
  });
}

export function useReporteRango(params: Parameters<typeof reportesApi.rango>[0]) {
  return useQuery({
    queryKey: ["reportes", "rango", params],
    queryFn:  () => reportesApi.rango(params),
    enabled:  !!params?.desde && !!params?.hasta,
  });
}

export function useReporteDia(params: Parameters<typeof reportesApi.dia>[0]) {
  return useQuery({
    queryKey: ["reportes", "dia", params],
    queryFn:  () => reportesApi.dia(params),
    enabled:  !!params.sucursal_id,
  });
}

/** ─── ML ───────────────────────────────────────────────── */
export function useMlStatus() {
  return useQuery({
    queryKey: ["ml", "status"],
    queryFn:  () => mlApi.status(),
    staleTime: 30_000,
  });
}

export function useMlForecast(productoId: string | undefined) {
  return useQuery({
    queryKey: ["ml", "forecast", productoId],
    queryFn:  () => mlApi.forecast(productoId!),
    enabled:  !!productoId,
  });
}

export function useMlAlertas(params?: {
  sucursal_id?:    string;
  incluir_leidas?: boolean;
  severidad?:      AlertaSeveridad;
  tipo?:           AlertaTipo;
}) {
  return useQuery({
    queryKey: ["ml", "alerts", params],
    queryFn:  () => mlApi.alerts(params),
    staleTime: 30_000,
  });
}

export function useAcknowledgeMlAlerta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => mlApi.acknowledgeAlert(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ml", "alerts"] });
      qc.invalidateQueries({ queryKey: ["ml", "status"] });
    },
    onError: (e) => handleError(e, "Error al marcar alerta"),
  });
}

export function useMlRestockSuggestions(params?: {
  sucursal_id?:    string;
  horizonte_dias?: number;
}) {
  return useQuery({
    queryKey: ["ml", "restock", params],
    queryFn:  () => mlApi.restockSuggestions(params),
  });
}

export function useTrainMl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params?: Parameters<typeof mlApi.train>[0]) => mlApi.train(params),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["ml"] });
      toast.success(
        `Entrenamiento completo: ${data.modelos_entrenados} modelos, ${data.alertas_creadas} alertas`
      );
    },
    onError: (e) => handleError(e, "Error en entrenamiento ML"),
  });
}

/** ─── BRANDING ───────────────────────────────── */
export function useBrandingQuery(
  opts?: Omit<UseQueryOptions<Awaited<ReturnType<typeof brandingApi.get>>>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: ["branding"],
    queryFn:  () => brandingApi.get(),
    staleTime: 5 * 60_000,
    ...opts,
  });
}

export function useUpdateBranding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BrandingUpdateRequest) => brandingApi.update(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["branding"] });
      toast.success("Branding actualizado");
    },
    onError: (e) => handleError(e, "Error al actualizar branding"),
  });
}

/** ─── USUARIOS (operativos: cajero, manager, inventario) ─── */
export function useUsuarios() {
  return useQuery({
    queryKey: ["usuarios"],
    queryFn:  () => usuariosApi.list(),
    staleTime: 30_000,
  });
}

export function useCrearUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CrearUsuarioRequest) => usuariosApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["usuarios"] });
      toast.success("Usuario creado");
    },
    onError: (e) => handleError(e, "Error al crear usuario"),
  });
}

export function useActualizarUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: number; data: Parameters<typeof usuariosApi.update>[1] }) =>
      usuariosApi.update(input.id, input.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["usuarios"] });
      toast.success("Usuario actualizado");
    },
    onError: (e) => handleError(e, "Error al actualizar usuario"),
  });
}

export function useEliminarUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => usuariosApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["usuarios"] });
      toast.success("Usuario desactivado");
    },
    onError: (e) => handleError(e, "Error al desactivar usuario"),
  });
}

/** ─── MESAS ──────────────────────────────────────────── */
export function useMesas(sucursalId?: string) {
  return useQuery({
    queryKey: ["mesas", sucursalId],
    queryFn: () => mesasApi.list(sucursalId ? { sucursal_id: sucursalId } : undefined),
    refetchInterval: 15000,
  });
}

export function useActualizarMesaEstado() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & import("@/lib/api/mesas").MesaEstadoUpdate) =>
      mesasApi.updateEstado(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mesas"] });
    },
    onError: (e) => handleError(e, "Error al actualizar mesa"),
  });
}
