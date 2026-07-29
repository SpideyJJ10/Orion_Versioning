import { api } from "./client";

export interface MesaOut {
  id: string;
  sucursal_id: string;
  numero: number;
  nombre: string | null;
  capacidad: number;
  estado: "libre" | "ocupada" | "reservada" | "cuenta_pedida";
  orden_id: string | null;
  notas: string | null;
  activo: boolean;
}

export interface MesaCreate {
  numero: number;
  nombre?: string | null;
  capacidad: number;
  sucursal_id: string;
}

export interface MesaUpdate {
  nombre?: string | null;
  capacidad?: number;
  activo?: boolean;
}

export interface MesaEstadoUpdate {
  estado: "libre" | "ocupada" | "reservada" | "cuenta_pedida";
  orden_id?: string | null;
  notas?: string | null;
}

export const mesasApi = {
  list: (params?: { sucursal_id?: string; solo_activas?: boolean }) =>
    api.get<MesaOut[]>("/api/mesas", { params }),
  
  create: (data: MesaCreate) => 
    api.post<MesaOut>("/api/mesas", data),
    
  update: (id: string, data: MesaUpdate) => 
    api.patch<MesaOut>(`/api/mesas/${id}`, data),
    
  updateEstado: (id: string, data: MesaEstadoUpdate) => 
    api.patch<MesaOut>(`/api/mesas/${id}/estado`, data),
    
  delete: (id: string) => 
    api.delete<{ success: boolean }>(`/api/mesas/${id}`),
};
