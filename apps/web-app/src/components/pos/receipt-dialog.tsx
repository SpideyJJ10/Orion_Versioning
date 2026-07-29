"use client";

import { useEffect, useRef } from "react";
import { Printer, Check } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useReciboOrden } from "@/lib/hooks/use-api";
import { formatCurrency, formatDateTime, formatQuantity } from "@/lib/formatters";

interface ReceiptDialogProps {
  ordenId:      string | null;
  open:         boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Diálogo de recibo imprimible. Trae los datos vivos vía
 * `useReciboOrden(ordenId)` y dibuja un ticket de 80mm.
 *
 * Soporta `window.print()` con un stylesheet inline que oculta el resto
 * del UI. Para ESC/POS real (futuro), se podría enviar el JSON vía WebUSB.
 */
export function ReceiptDialog({ ordenId, open, onOpenChange }: ReceiptDialogProps) {
  const { data, isLoading } = useReciboOrden(open ? (ordenId ?? undefined) : undefined);
  const printRef = useRef<HTMLDivElement>(null);

  // Atajo: ⌘/Ctrl + P imprime cuando el diálogo está abierto.
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "p") {
        e.preventDefault();
        window.print();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Recibo de venta</DialogTitle>
        </DialogHeader>

        {isLoading || !data ? (
          <div className="space-y-2 py-4">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-6 w-full" />
          </div>
        ) : (
          <div ref={printRef} id="orion-print-area" className="space-y-3 font-mono text-xs">
            <header className="text-center">
              {data.negocio.logo_url && (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={data.negocio.logo_url}
                  alt={data.negocio.nombre_comercial}
                  className="mx-auto mb-1 h-10 w-auto"
                />
              )}
              <div className="text-sm font-bold uppercase tracking-wide">
                {data.negocio.nombre_comercial}
              </div>
              {data.negocio.sucursal && (
                <div className="text-[11px]">{data.negocio.sucursal}</div>
              )}
              {data.negocio.telefono && (
                <div className="text-[11px]">Tel: {data.negocio.telefono}</div>
              )}
            </header>

            <div className="border-t border-dashed pt-2">
              <div className="flex justify-between">
                <span>Recibo:</span>
                <span className="font-semibold">{data.orden.id.slice(0, 8).toUpperCase()}</span>
              </div>
              <div className="flex justify-between">
                <span>Fecha:</span>
                <span>{formatDateTime(data.orden.fecha)}</span>
              </div>
              {data.orden.cliente_nombre && (
                <div className="flex justify-between">
                  <span>Cliente:</span>
                  <span>{data.orden.cliente_nombre}</span>
                </div>
              )}
            </div>

            <div className="border-t border-dashed pt-2">
              <div className="grid grid-cols-[1fr_auto_auto] gap-x-2 text-[11px]">
                <span className="font-bold">Producto</span>
                <span className="text-right font-bold">Cant.</span>
                <span className="text-right font-bold">Total</span>
                {data.orden.items.map((it) => (
                  <ItemRow key={it.id} item={it} />
                ))}
              </div>
            </div>

            <div className="space-y-0.5 border-t border-dashed pt-2">
              <Row label="Subtotal" value={formatCurrency(data.orden.subtotal)} />
              {data.orden.descuento > 0 && (
                <Row label="Descuento" value={`-${formatCurrency(data.orden.descuento)}`} />
              )}
              {data.orden.domicilio > 0 && (
                <Row label="Domicilio" value={formatCurrency(data.orden.domicilio)} />
              )}
              <Row
                label="TOTAL"
                value={formatCurrency(data.orden.total)}
                strong
              />
            </div>

            <div className="space-y-0.5 border-t border-dashed pt-2">
              <Row label="Pago" value={data.pago.metodo} />
              {data.pago.efectivo_recibido !== null && (
                <Row label="Recibido" value={formatCurrency(data.pago.efectivo_recibido)} />
              )}
              {data.pago.cambio !== null && data.pago.cambio > 0 && (
                <Row label="Cambio" value={formatCurrency(data.pago.cambio)} />
              )}
              {data.pago.pagos_mixtos.length > 0 && (
                <div className="mt-1 space-y-0.5">
                  {data.pago.pagos_mixtos.map((p, i) => (
                    <Row
                      key={i}
                      label={`  ${p.metodo}`}
                      value={formatCurrency(p.monto)}
                    />
                  ))}
                </div>
              )}
            </div>

            <p className="border-t border-dashed pt-2 text-center text-[11px]">
              ¡Gracias por su compra!
            </p>
          </div>
        )}

        <DialogFooter className="gap-2 sm:justify-between print:hidden">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            <Check className="mr-1 h-4 w-4" />
            Cerrar
          </Button>
          <Button onClick={() => window.print()} disabled={!data}>
            <Printer className="mr-1 h-4 w-4" />
            Imprimir
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between ${strong ? "text-sm font-bold" : ""}`}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}

function ItemRow({ item }: { item: { producto_nombre: string; cantidad: number; precio_unitario: number; total: number } }) {
  return (
    <>
      <span className="col-span-3 mt-1 truncate font-medium">{item.producto_nombre}</span>
      <span className="text-muted-foreground">
        {formatQuantity(item.cantidad)} × {formatCurrency(item.precio_unitario)}
      </span>
      <span />
      <span className="text-right">{formatCurrency(item.total)}</span>
    </>
  );
}
