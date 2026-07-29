import { api } from "./client";
import type {
  ForecastResponse,
  MlAlerta,
  RestockSuggestion,
  MlStatus,
  MlTrainResult,
  AlertaSeveridad,
  AlertaTipo,
} from "./types";

export const mlApi = {
  forecast: (productoId: string) =>
    api.get<ForecastResponse>(`/api/v3/ml/forecast/${productoId}`),

  alerts: (params?: {
    sucursal_id?:    string;
    incluir_leidas?: boolean;
    severidad?:      AlertaSeveridad;
    tipo?:           AlertaTipo;
    limit?:          number;
  }) => api.get<MlAlerta[]>("/api/v3/ml/alerts", { params }),

  acknowledgeAlert: (id: number) =>
    api.patch<MlAlerta>(`/api/v3/ml/alerts/${id}/acknowledge`),

  restockSuggestions: (params?: { sucursal_id?: string; horizonte_dias?: number }) =>
    api.get<RestockSuggestion[]>("/api/v3/ml/restock-suggestions", { params }),

  status: () => api.get<MlStatus>("/api/v3/ml/status"),

  train: (params?: {
    sucursal_id?:    string;
    horizonte_dias?: number;
    historial_dias?: number;
    sincrono?:       boolean;
  }) => api.post<MlTrainResult>("/api/v3/ml/train", undefined, { params }),
};
