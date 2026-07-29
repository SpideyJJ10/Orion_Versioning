import { api } from "./client";
import type { ReporteDia, ReporteDiario, ReporteRango } from "./types";

export const reportesApi = {
  /** KPIs unificados del día (consumido por el dashboard). */
  diario: (params?: { sucursal_id?: string; fecha?: string; tz_offset?: number }) =>
    api.get<ReporteDiario>("/api/reportes/diario", { params }),

  /** KPIs agregados + serie diaria para gráficas (pantalla de Reportes). */
  rango: (params: {
    desde:        string;
    hasta:        string;
    sucursal_id?: string;
    tz_offset?:   number;
  }) => api.get<ReporteRango>("/api/reportes/rango", { params }),

  /** Cierre de caja legacy (resumen por método de pago + lista productos). */
  dia: (params: { sucursal_id: string; fecha?: string; tz_offset?: number }) =>
    api.get<ReporteDia>("/api/reportes/dia", { params }),
};
