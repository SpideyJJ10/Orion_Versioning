"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAjusteStock } from "@/lib/hooks/use-api";
import { formatQuantity } from "@/lib/formatters";
import type { Producto } from "@/lib/api/types";

const MOTIVOS = [
  { value: "compra",     label: "Compra a proveedor"     },
  { value: "merma",      label: "Merma / pérdida"        },
  { value: "ajuste",     label: "Ajuste de inventario"   },
  { value: "devolucion", label: "Devolución de cliente"  },
  { value: "transfer",   label: "Transferencia entre sedes" },
];

interface AjusteStockDialogProps {
  open:         boolean;
  onOpenChange: (open: boolean) => void;
  producto:     Producto | null;
}

/**
 * Diálogo de ajuste manual de stock.
 *
 * Permite registrar entradas o salidas con motivo. El backend crea un
 * `MovimientoInventario` (ledger) y actualiza `Producto.stock` en una
 * transacción atómica.
 */
export function AjusteStockDialog({ open, onOpenChange, producto }: AjusteStockDialogProps) {
  const [tipo,     setTipo]     = useState<"entrada" | "salida">("entrada");
  const [cantidad, setCantidad] = useState<string>("");
  const [motivo,   setMotivo]   = useState<string>("compra");

  const ajuste = useAjusteStock();

  useEffect(() => {
    if (open) {
      setTipo("entrada");
      setCantidad("");
      setMotivo("compra");
    }
  }, [open]);

  if (!producto) return null;

  const cantidadNum = Number(cantidad) || 0;
  const cantidadSigned = tipo === "entrada" ? cantidadNum : -cantidadNum;
  const stockResultante = producto.stock + cantidadSigned;
  const cantidadInvalida =
    cantidadNum <= 0 || (tipo === "salida" && stockResultante < 0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (cantidadInvalida || !producto) return;
    try {
      await ajuste.mutateAsync({
        productoId: producto.id,
        data: { cantidad: cantidadSigned, motivo },
      });
      onOpenChange(false);
    } catch {
      /* toast en hook */
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Ajustar stock</DialogTitle>
          <DialogDescription>
            <span className="font-medium text-foreground">{producto.nombre}</span> ·
            stock actual:{" "}
            <span className="font-semibold text-foreground">
              {formatQuantity(producto.stock, producto.unidad_medida)}
            </span>
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Tipo (entrada/salida) */}
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setTipo("entrada")}
              className={`rounded-md border px-3 py-2 text-sm font-medium transition ${
                tipo === "entrada"
                  ? "border-success bg-success/10 text-success"
                  : "border-border bg-card text-muted-foreground hover:border-success/50"
              }`}
            >
              + Entrada
            </button>
            <button
              type="button"
              onClick={() => setTipo("salida")}
              className={`rounded-md border px-3 py-2 text-sm font-medium transition ${
                tipo === "salida"
                  ? "border-destructive bg-destructive/10 text-destructive"
                  : "border-border bg-card text-muted-foreground hover:border-destructive/50"
              }`}
            >
              − Salida
            </button>
          </div>

          <div className="space-y-1">
            <Label htmlFor="cantidad">Cantidad ({producto.unidad_medida})</Label>
            <Input
              id="cantidad"
              type="number"
              step="0.001"
              inputMode="decimal"
              min={0}
              value={cantidad}
              onChange={(e) => setCantidad(e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground">
              Resultado:{" "}
              <span className={stockResultante < 0 ? "font-semibold text-destructive" : "font-semibold"}>
                {formatQuantity(Math.max(0, stockResultante), producto.unidad_medida)}
              </span>
            </p>
          </div>

          <div className="space-y-1">
            <Label htmlFor="motivo">Motivo</Label>
            <Select value={motivo} onValueChange={setMotivo}>
              <SelectTrigger id="motivo">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MOTIVOS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter className="gap-2 sm:justify-between">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={ajuste.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={cantidadInvalida || ajuste.isPending}>
              {ajuste.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Confirmar
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
