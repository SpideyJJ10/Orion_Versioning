import { api } from "./client";
import type {
  TokenPair,
  UsuarioPublico,
  CrearUsuarioRequest,
  LoginRequest,
  LoginPinRequest,
  RegisterRequest,
} from "./types";

export const authApi = {
  /** Registra un negocio nuevo (tenant + owner). */
  register: (data: RegisterRequest) =>
    api.post<TokenPair>("/api/v3/auth/register", data, { auth: false }),

  /** Login email + password. */
  login: (data: LoginRequest) =>
    api.post<TokenPair>("/api/v3/auth/login", data, { auth: false }),

  /** Login rápido por PIN (cajero/manager). */
  loginPin: (data: LoginPinRequest) =>
    api.post<TokenPair>("/api/v3/auth/login-pin", data, { auth: false }),

  /** Renueva access_token con un refresh_token válido. */
  refresh: (refresh_token: string) =>
    api.post<TokenPair>("/api/v3/auth/refresh", { refresh_token }, { auth: false }),

  /** Datos del usuario autenticado. */
  me: () => api.get<UsuarioPublico>("/api/v3/auth/me"),
};

export const usuariosApi = {
  /** Lista los usuarios operativos del tenant (manager/cajero/inventario). */
  list: () => api.get<UsuarioPublico[]>("/api/v3/usuarios"),

  /** Owner/manager crea un usuario operativo. */
  create: (data: CrearUsuarioRequest) =>
    api.post<UsuarioPublico>("/api/v3/usuarios", data),

  /** Actualiza datos básicos (nombre, rol, sucursal, PIN, password). */
  update: (id: number, data: Partial<{
    nombre:      string;
    rol:         CrearUsuarioRequest["rol"];
    sucursal_id: string | null;
    pin:         string | null;
    password:    string;
    activo:      boolean;
  }>) => api.put<UsuarioPublico>(`/api/v3/usuarios/${id}`, data),

  /** Soft-delete: desactiva al usuario. */
  delete: (id: number) => api.delete<void>(`/api/v3/usuarios/${id}`),
};
