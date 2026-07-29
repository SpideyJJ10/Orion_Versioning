"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Plus, Trash2, Wallet, CreditCard, Smartphone, Landmark, Coins } from "lucide-react";

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
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/formatters";
import { useCartStore } from "@/lib/stores/cart-store";
import type { MetodoPago, PagoMixto } from "@/lib/api/types";

const METODOS: { value: MetodoPago; label: string; Icon: typeof Wallet }[] = [
  { value: "Efectivo",      label: "Efectivo",      Icon: Wallet },
  { value: "Nequi",         label: "Nequi",         Icon: Smartphone },
  { value: "Daviplata",     label: "Daviplata",     Icon: Smartphone },
  { value: "Tarjeta",       label: "Tarjeta",       Icon: CreditCard },
  { value: "Transferencia", label: "Transferencia", Icon: Landmark },
  { value: "Mixto",         label: "Pago mixto",    Icon: Coins },
];

interface CheckoutDialogProps {
  open:        boolean;
  onOpenChange: (open: boolean) => void;
  /** Se llama cuando el usuario confirma el pago. */
  onConfirm:   () => void;
  isPending?:  boolean;
}

/**
 * Diálogo de cobro: método de pago, efectivo recibido + cambio,
 * pagos mixtos, cliente, notas y domicilio.
 *
 * Se valida que el monto de pagos mixtos cubra el total antes de habilitar
 * el botón "Cobrar". También se calcula el cambio en tiempo real.
 */
export function CheckoutDialog({ open, onOpenChange, onConfirm, isPending }: CheckoutDialogProps) {
  const {
    metodo_pago, setMetodoPago,
    descuento,   setDescuento,
    domicilio,   setDomicilio,
    cliente,     setCliente,
    notas,       setNotas,
    efectivo_recibido, setEfectivoRecibido,
    pagos_mixtos,      setPagosMixtos,
    items, subtotal, total, cambio,
  } = useCartStore();

  const sub  = subtotal();
  const tot  = total();
  const ch   = cambio();

  // ─────────────────────────────────────────────
  // Validaciones
  // ─────────────────────────────────────────────
  const efectivoFaltante =
    metodo_pago === "Efectivo" &&
    efectivo_recibido !== null &&
    efectivo_recibido < tot;

  const sumaMixtos = useMemo(
    () => pagos_mixtos.reduce((acc, p) => acc + (p.monto || 0), 0),
    [pagos_mixtos],
  );
  const mixtoIncompleto = metodo_pago === "Mixto" && Math.abs(sumaMixtos - tot) > 0.5;

  const canConfirm =
    items.length > 0 &&
    !isPending &&
    !mixtoIncompleto &&
    (metodo_pago !== "Efectivo" || efectivo_recibido === null || !efectivoFaltante);

  // Cuando se abre el diálogo, sugerimos el efectivo == total para acelerar.
  useEffect(() => {
    if (open && metodo_pago === "Efectivo" && efectivo_recibido === null) {
      setEfectivoRecibido(tot);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // ─────────────────────────────────────────────
  // Pagos mixtos
  // ─────────────────────────────────────────────
  function addPagoMixto() {
    const restante = Math.max(0, tot - sumaMixtos);
    setPagosMixtos([...pagos_mixtos, { metodo: "Efectivo", monto: restante }]);
  }
  function updatePagoMixto(idx: number, patch: Partial<PagoMixto>) {
    setPagosMixtos(pagos_mixtos.map((p, i) => (i === idx ? { ...p, ...patch } : p)));
  }
  function removePagoMixto(idx: number) {
    setPagosMixtos(pagos_mixtos.filter((_, i) => i !== idx));
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Cobrar venta</DialogTitle>
          <DialogDescription>
            Total a cobrar:{" "}
            <span className="font-semibold text-foreground">{formatCurrency(tot)}</span>
          </DialogDescription>
        </DialogHeader>

        {/* ── Método de pago (grid de iconos) ── */}
        <div className="grid grid-cols-3 gap-2">
          {METODOS.map(({ value, label, Icon }) => {
            const active = metodo_pago === value;
            return (
              <button
                key={value}
                type="button"
                onClick={() => setMetodoPago(value)}
                className={cn(
                  "flex flex-col items-center justify-center gap-1 rounded-md border p-3 text-xs font-medium transition",
                  active
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-card hover:border-primary/50",
                )}
              >
                <Icon className="h-5 w-5" />
                {label}
              </button>
            );
          })}
        </div>

        {/* ── Inputs de efectivo / mixto ── */}
        {metodo_pago === "Efectivo" && (
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="efectivo">Efectivo recibido</Label>
              <Input
                id="efectivo"
                type="number"
                inputMode="decimal"
                step="100"
                min={0}
                value={efectivo_recibido ?? ""}
                onChange={(e) =>
                  setEfectivoRecibido(e.target.value === "" ? null : Number(e.target.value))
                }
                className={cn(efectivoFaltante && "border-destructive")}
              />
            </div>
            <div className="space-y-1">
              <Label>Cambio</Label>
              <div className={cn(
                "flex h-9 items-center rounded-md border bg-muted/40 px-3 text-sm font-semibold",
                efectivoFaltante && "text-destructive",
              )}>
                {efectivoFaltante
                  ? `Faltan ${formatCurrency(tot - (efectivo_recibido ?? 0))}`
                  : formatCurrency(ch)}
              </div>
            </div>
          </div>
        )}

        {metodo_pago === "Mixto" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                Suma:{" "}
                <span className={cn(
                  "font-semibold",
                  mixtoIncompleto ? "text-destructive" : "text-success",
                )}>
                  {formatCurrency(sumaMixtos)}
                </span>{" "}
                / {formatCurrency(tot)}
              </span>
              <Button type="button" variant="outline" size="sm" onClick={addPagoMixto}>
                <Plus className="h-3 w-3" />
                Agregar
              </Button>
            </div>
            {pagos_mixtos.length === 0 && (
              <p className="rounded-md border border-dashed py-3 text-center text-xs text-muted-foreground">
                Agrega al menos dos pagos para completar el total.
              </p>
            )}
            {pagos_mixtos.map((p, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <Select
                  value={p.metodo}
                  onValueChange={(v) => updatePagoMixto(idx, { metodo: v as MetodoPago })}
                >
                  <SelectTrigger className="h-9 w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {METODOS.filter((m) => m.value !== "Mixto").map((m) => (
                      <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  type="number"
                  inputMode="decimal"
                  step="100"
                  value={p.monto}
                  onChange={(e) =>
                    updatePagoMixto(idx, { monto: Number(e.target.value) || 0 })
                  }
                  className="h-9 flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removePagoMixto(idx)}
                  aria-label="Eliminar pago"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}

        <Separator />

        {/* ── Datos opcionales ── */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label htmlFor="descuento">Descuento</Label>
            <Input
              id="descuento"
              type="number"
              inputMode="decimal"
              step="100"
              min={0}
              max={sub}
              value={descuento || ""}
              onChange={(e) => setDescuento(Number(e.target.value) || 0)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="domicilio">Domicilio</Label>
            <Input
              id="domicilio"
              type="number"
              inputMode="decimal"
              step="100"
              min={0}
              value={domicilio || ""}
              onChange={(e) => setDomicilio(Number(e.target.value) || 0)}
            />
          </div>
          <div className="col-span-2 space-y-1">
            <Label htmlFor="cliente">Cliente (opcional)</Label>
            <Input
              id="cliente"
              value={cliente}
              onChange={(e) => setCliente(e.target.value)}
              placeholder="Nombre del cliente"
            />
          </div>
          <div className="col-span-2 space-y-1">
            <Label htmlFor="notas">Notas (opcional)</Label>
            <Textarea
              id="notas"
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              rows={2}
              placeholder="Detalles, mesa, ubicación de envío..."
            />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:justify-between">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancelar
          </Button>
          <Button onClick={onConfirm} disabled={!canConfirm} className="min-w-32">
            {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Cobrar {formatCurrency(tot)}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
