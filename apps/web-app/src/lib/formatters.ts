import { format, formatDistanceToNow, parseISO } from "date-fns";
import { es } from "date-fns/locale";

/** Moneda y locale por defecto del MVP (Orion nace en Colombia). */
export const DEFAULT_CURRENCY = "USD";
export const DEFAULT_LOCALE   = "en-US";

/**
 * Formatea un número como moneda local. Para USD muestra hasta 2.
 */
export function formatCurrency(
  value: number | string | null | undefined,
  currency: string = DEFAULT_CURRENCY,
  locale:   string = DEFAULT_LOCALE
): string {
  const n = typeof value === "string" ? Number(value) : value;
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat(locale, {
    style:                 "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

/** Formatea un número con separadores de miles. */
export function formatNumber(
  value: number | null | undefined,
  fractionDigits: number = 0,
  locale: string = DEFAULT_LOCALE,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

/**
 * Formatea una cantidad con su unidad de medida.
 * - Para `unidad` muestra entero ("3 ud").
 * - Para `kg|lt|gr|ml` muestra hasta 3 decimales sin ceros sobrantes ("0.5 kg").
 */
export function formatQuantity(
  value: number | null | undefined,
  unidad: string = "unidad",
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const u = (unidad || "unidad").toLowerCase();
  const isDecimal = ["kg", "lt", "gr", "ml"].includes(u);
  const decimals  = isDecimal ? Math.min(3, ((value % 1) === 0 ? 0 : 3)) : 0;
  const text = new Intl.NumberFormat(DEFAULT_LOCALE, {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(value);
  const label =
    u === "unidad" ? (value === 1 ? "ud" : "ud")
    : u === "pack"  ? "pk"
    : u === "caja"  ? "cj"
    : u === "docena" ? "dz"
    : u;
  return `${text} ${label}`;
}

/** "30 abr 2026" */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return format(parseISO(iso), "d MMM yyyy", { locale: es });
  } catch {
    return iso;
  }
}

/** "hace 3 horas", "hace 2 días" */
export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true, locale: es });
  } catch {
    return iso;
  }
}

/** "30 abr 2026 14:30" */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return format(parseISO(iso), "d MMM yyyy HH:mm", { locale: es });
  } catch {
    return iso;
  }
}

/**
 * Parsea un string "YYYY-MM-DD HH:MM:SS" (formato del backend para órdenes)
 * o un ISO completo. Devuelve `null` si no es parseable.
 */
export function parseBackendDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  try {
    // El backend devuelve "YYYY-MM-DD HH:MM:SS" para Orden.fecha
    const normalized = value.includes("T") ? value : value.replace(" ", "T");
    const d = new Date(normalized);
    return Number.isNaN(d.getTime()) ? null : d;
  } catch {
    return null;
  }
}

/**
 * Convierte HSL en CSS-vars-string: "250 84% 54%" → ["250", "84%", "54%"]
 */
export function hslFromHex(hex: string): string {
  // Limpia #
  const h = hex.replace("#", "");
  if (h.length !== 6) return "250 84% 54%"; // fallback

  const r = parseInt(h.slice(0, 2), 16) / 255;
  const g = parseInt(h.slice(2, 4), 16) / 255;
  const b = parseInt(h.slice(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;

  let hue = 0;
  let sat = 0;

  if (max !== min) {
    const d = max - min;
    sat = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: hue = ((g - b) / d + (g < b ? 6 : 0)); break;
      case g: hue = ((b - r) / d + 2);               break;
      case b: hue = ((r - g) / d + 4);               break;
    }
    hue *= 60;
  }

  return `${Math.round(hue)} ${Math.round(sat * 100)}% ${Math.round(l * 100)}%`;
}
