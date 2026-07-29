"use client";

import { memo } from "react";
import Image from "next/image";
import { Package } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatCurrency, formatQuantity } from "@/lib/formatters";
import type { Producto } from "@/lib/api/types";

interface ProductCardProps {
  product:  Producto;
  onSelect: (product: Producto) => void;
  disabled?: boolean;
}

/**
 * Tarjeta táctil del catálogo POS.
 * - Muestra imagen del producto (o ícono fallback) y badge de categoría.
 * - Resalta `stock` con la unidad de medida correcta (decimales en kg/lt).
 * - Se desactiva si está sin stock; ofrece feedback visual claro.
 */
export const ProductCard = memo(function ProductCard({ product, onSelect, disabled }: ProductCardProps) {
  const outOfStock = product.stock <= 0;
  const lowStock   = !outOfStock && product.stock <= product.stock_minimo;

  return (
    <button
      type="button"
      onClick={() => !outOfStock && !disabled && onSelect(product)}
      disabled={outOfStock || disabled}
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-lg border bg-card text-left shadow-sm transition",
        "hover:border-primary hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary",
        (outOfStock || disabled) &&
          "cursor-not-allowed opacity-60 hover:border-border hover:shadow-sm",
      )}
    >
      <div className="relative aspect-[4/3] w-full bg-muted/40">
        {product.imagen_url ? (
          product.imagen_url.startsWith("http") ? (
            <img
              src={product.imagen_url}
              alt={product.nombre}
              className="h-full w-full object-cover"
            />
          ) : (
            <Image
              src={product.imagen_url}
              alt={product.nombre}
              fill
              sizes="(max-width: 768px) 33vw, 200px"
              className="object-cover"
              unoptimized
            />
          )
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Package className="h-10 w-10 text-muted-foreground/40" />
          </div>
        )}
        {product.categoria && (
          <span className="absolute left-2 top-2 rounded-full bg-background/80 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground backdrop-blur">
            {product.categoria}
          </span>
        )}
        {outOfStock && (
          <span className="absolute right-2 top-2 rounded-full bg-destructive px-2 py-0.5 text-[10px] font-bold text-destructive-foreground">
            Agotado
          </span>
        )}
        {lowStock && (
          <span className="absolute right-2 top-2 rounded-full bg-warning px-2 py-0.5 text-[10px] font-bold text-warning-foreground">
            Bajo
          </span>
        )}
      </div>
      <div className="flex flex-col gap-1 p-3">
        <span className="line-clamp-2 text-sm font-medium leading-tight">
          {product.nombre}
        </span>
        <div className="flex items-end justify-between">
          <span className="text-base font-semibold">
            {formatCurrency(product.precio)}
          </span>
          <span
            className={cn(
              "text-[11px]",
              outOfStock ? "text-destructive" : "text-muted-foreground",
            )}
          >
            {formatQuantity(product.stock, product.unidad_medida)}
          </span>
        </div>
      </div>
    </button>
  );
});
ProductCard.displayName = "ProductCard";
