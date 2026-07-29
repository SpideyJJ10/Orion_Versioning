"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";

type Variant = "full" | "mark" | "wordmark";
type Size    = "sm" | "md" | "lg" | "xl";

interface OrionLogoProps {
  /** "full" = isotipo + wordmark, "mark" = solo gema, "wordmark" = solo texto. */
  variant?:  Variant;
  size?:     Size;
  /** Si el tenant tiene logo personalizado, se prioriza sobre el de Orion. */
  tenantLogoUrl?: string | null;
  /** Texto del wordmark (default: "Orion"). Se ignora con variant="mark". */
  label?:    string;
  className?: string;
}

const SIZE_CLASS: Record<Size, { mark: string; text: string; gap: string }> = {
  sm: { mark: "h-6 w-6",   text: "text-sm",  gap: "gap-2" },
  md: { mark: "h-9 w-9",   text: "text-base", gap: "gap-2.5" },
  lg: { mark: "h-12 w-12", text: "text-xl",  gap: "gap-3" },
  xl: { mark: "h-20 w-20", text: "text-3xl", gap: "gap-4" },
};

/**
 * Marca oficial de Orion.
 *
 * - `mark`     → solo isotipo (gema azul + Z), ideal para favicons o sidebars colapsadas.
 * - `wordmark` → solo el texto, con degradado de marca.
 * - `full`     → isotipo + wordmark.
 *
 * Si el tenant tiene un `logo_url` definido en su branding, se respeta
 * (white-label); en otro caso se renderiza el logo Orion.
 */
export function OrionLogo({
  variant       = "full",
  size          = "md",
  tenantLogoUrl,
  label         = "Orion",
  className,
}: OrionLogoProps) {
  const s = SIZE_CLASS[size];

  if (variant === "wordmark") {
    return (
      <span
        className={cn(
          "bg-clip-text font-extrabold tracking-tight text-transparent",
          "bg-gradient-to-br from-[#d946ef] via-[#a855f7] to-[#6366f1]",
          s.text,
          className,
        )}
      >
        {label}
      </span>
    );
  }

  const markSrc = tenantLogoUrl || "/orion-logo-mark.png";
  const altText = tenantLogoUrl ? `${label} logo` : "Orion";

  if (variant === "mark") {
    return (
      <span className={cn("relative inline-block", s.mark, className)}>
        {markSrc.startsWith("http") ? (
          <img
            src={markSrc}
            alt={altText}
            className="h-full w-full object-contain"
          />
        ) : (
          <Image
            src={markSrc}
            alt={altText}
            fill
            sizes="64px"
            priority
            className="object-contain"
          />
        )}
      </span>
    );
  }

  return (
    <span className={cn("inline-flex items-center", s.gap, className)}>
      <span className={cn("relative inline-block", s.mark)}>
        {markSrc.startsWith("http") ? (
          <img
            src={markSrc}
            alt={altText}
            className="h-full w-full object-contain"
          />
        ) : (
          <Image
            src={markSrc}
            alt={altText}
            fill
            sizes="80px"
            priority
            className="object-contain"
          />
        )}
      </span>
      <span
        className={cn(
          "font-extrabold tracking-tight",
          "bg-clip-text text-transparent bg-gradient-to-br from-[#d946ef] via-[#a855f7] to-[#6366f1]",
          s.text,
        )}
      >
        {label}
      </span>
    </span>
  );
}
