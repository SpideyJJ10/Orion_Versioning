"use client";

import { Minus, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface QuantityInputProps {
  value:    number;
  /** Unidad de medida del producto: define el step y el formato. */
  unidad?:  string;
  min?:     number;
  max?:     number;
  onChange: (next: number) => void;
  className?: string;
  size?:    "sm" | "md";
}

/**
 * Selector de cantidad con +/- y entrada numérica directa.
 *
 * - Para unidades discretas (`unidad`, `pack`, `caja`, `docena`) usa step 1.
 * - Para unidades continuas (`kg`, `lt`, `gr`, `ml`) usa step 0.1.
 * - Respeta `max` (típicamente el stock disponible) y muestra un estado
 *   visual cuando el usuario lo excede.
 */
export function QuantityInput({
  value,
  unidad   = "unidad",
  min      = 0,
  max,
  onChange,
  className,
  size     = "md",
}: QuantityInputProps) {
  const u    = (unidad || "unidad").toLowerCase();
  const step = ["kg", "lt", "gr", "ml"].includes(u) ? 0.1 : 1;
  const exceeds = max !== undefined && value > max;

  const dec = () => onChange(Math.max(min, round3(value - step)));
  const inc = () => {
    const next = round3(value + step);
    onChange(max !== undefined ? Math.min(max, next) : next);
  };

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 rounded-md border bg-background",
        exceeds && "border-destructive",
        className,
      )}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className={size === "sm" ? "h-7 w-7" : "h-8 w-8"}
        onClick={dec}
        aria-label="Reducir"
      >
        <Minus className="h-3.5 w-3.5" />
      </Button>
      <Input
        type="number"
        inputMode="decimal"
        step={step}
        min={min}
        max={max}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => {
          const v = parseFloat(e.target.value);
          onChange(Number.isFinite(v) ? round3(v) : 0);
        }}
        className={cn(
          "border-0 px-0 text-center focus-visible:ring-0",
          size === "sm" ? "h-7 w-14 text-xs" : "h-8 w-16 text-sm",
        )}
      />
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className={size === "sm" ? "h-7 w-7" : "h-8 w-8"}
        onClick={inc}
        aria-label="Aumentar"
      >
        <Plus className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function round3(n: number): number {
  return Math.round(n * 1000) / 1000;
}
