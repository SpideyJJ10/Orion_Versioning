import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Combina clases tailwind y resuelve conflictos.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Retorna `value` si es un objeto válido o `fallback` si no.
 */
export function pick<T extends Record<string, unknown>>(
  value: unknown,
  fallback: T
): T {
  return (value && typeof value === "object" ? value : fallback) as T;
}
