import { api } from "./client";

export interface TenantAdmin {
  id: number;
  email: string;
  nombre: string | null;
  plan: string;
  plan_activo: boolean;
  fecha_vencimiento: string | null;
  creado_en: string | null;
}

export interface PatchTenantData {
  plan_activo?: boolean;
  fecha_vencimiento?: string | null;
  nombre?: string;
  email?: string;
  plan?: string;
}

export const adminApi = {
  getTenants: () => {
    return api.get<TenantAdmin[]>("/api/admin/tenants");
  },
  updateTenant: (id: number, data: PatchTenantData) => {
    return api.patch<TenantAdmin>(`/api/admin/tenants/${id}`, data);
  },
  deleteTenant: (id: number) => {
    return api.delete<{ message: string; id: number }>(`/api/admin/tenants/${id}`);
  },
};
