/**
 * Cliente HTTP base con auto-refresh de tokens JWT.
 *
 * - Lee el access_token del store (zustand persistido en localStorage).
 * - Cuando recibe 401, intenta hacer refresh y reintenta la petición original.
 * - Si el refresh falla, dispara logout (redirect a /login).
 */
import { useAuthStore } from "@/lib/stores/auth-store";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Error tipado con status HTTP. */
export class ApiError extends Error {
  status:  number;
  payload: unknown;

  constructor(status: number, message: string, payload: unknown = null) {
    super(message);
    this.name    = "ApiError";
    this.status  = status;
    this.payload = payload;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Si false, no envía el access_token (útil para login/register). */
  auth?: boolean;
  /** Query params adicionales (los stringifyamos automáticamente). */
  params?: Record<string, string | number | boolean | null | undefined>;
}

/** Estado interno para no disparar 10 refresh en paralelo. */
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  // Si ya hay un refresh corriendo, espera a ese.
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (!refreshToken) {
      useAuthStore.getState().logout();
      throw new ApiError(401, "No refresh token");
    }

    const res = await fetch(`${API_URL}/api/v3/auth/refresh`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      useAuthStore.getState().logout();
      throw new ApiError(res.status, "Refresh failed");
    }

    const data = await res.json();
    useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
    return data.access_token as string;
  })()
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

function buildUrl(path: string, params?: RequestOptions["params"]): string {
  const url = new URL(
    path.startsWith("http") ? path : `${API_URL}${path}`,
    typeof window !== "undefined" ? window.location.origin : "http://localhost"
  );

  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== "") {
        url.searchParams.set(k, String(v));
      }
    });
  }
  // Si era ruta relativa, devolvemos solo path+search.
  if (!path.startsWith("http")) {
    return url.pathname + url.search;
  }
  return url.toString();
}

async function _request<T>(
  path:    string,
  options: RequestOptions = {},
  isRetry: boolean = false
): Promise<T> {
  const { body, auth = true, params, headers, ...rest } = options;

  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string> | undefined),
  };

  if (auth) {
    const token = useAuthStore.getState().accessToken;
    if (token) finalHeaders.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(buildUrl(path, params), {
    ...rest,
    headers: finalHeaders,
    body:    body !== undefined ? JSON.stringify(body) : undefined,
  });

  // 401 con auth → intenta refresh + reintenta
  if (res.status === 401 && auth && !isRetry) {
    try {
      await refreshAccessToken();
      return _request<T>(path, options, true);
    } catch {
      // Logout ya disparado dentro de refreshAccessToken
      throw new ApiError(401, "Sesión expirada");
    }
  }

  // 204 No Content
  if (res.status === 204) {
    return undefined as T;
  }

  let payload: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!res.ok) {
    let message = `Error ${res.status}`;
    if (payload && typeof payload === "object" && "detail" in payload) {
      const detail = (payload as { detail: unknown }).detail;
      if (Array.isArray(detail)) {
        // Pydantic validation error array
        message = detail.map((e: any) => {
          const field = e.loc?.slice(-1)[0] || "campo";
          return `${field}: ${e.msg}`;
        }).join(" | ");
      } else {
        message = String(detail);
      }
    }
    throw new ApiError(res.status, message, payload);
  }

  return payload as T;
}

export const api = {
  get<T>(path: string, options?: Omit<RequestOptions, "body">) {
    return _request<T>(path, { ...options, method: "GET" });
  },
  post<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "body" | "method">) {
    return _request<T>(path, { ...options, method: "POST", body });
  },
  put<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "body" | "method">) {
    return _request<T>(path, { ...options, method: "PUT", body });
  },
  patch<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "body" | "method">) {
    return _request<T>(path, { ...options, method: "PATCH", body });
  },
  delete<T>(path: string, options?: Omit<RequestOptions, "body">) {
    return _request<T>(path, { ...options, method: "DELETE" });
  },
};
