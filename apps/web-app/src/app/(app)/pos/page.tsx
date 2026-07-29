"use client";

import { useCallback, useMemo, useState } from "react";
import { ShoppingCart, Trash2, Search, Receipt as ReceiptIcon, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

import {
  useProductos,
  useSucursales,
  useCategorias,
  useCrearOrden,
} from "@/lib/hooks/use-api";
import { useCartStore } from "@/lib/stores/cart-store";
import { syncManager } from "@/lib/sync-manager";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { ProductCard } from "@/components/pos/product-card";
import { QuantityInput } from "@/components/pos/quantity-input";
import { CheckoutDialog } from "@/components/pos/checkout-dialog";
import { ReceiptDialog } from "@/components/pos/receipt-dialog";

import { useAuthStore } from "@/lib/stores/auth-store";
import { formatCurrency, formatQuantity } from "@/lib/formatters";
import type { Producto } from "@/lib/api/types";

const ALL_CATEGORIES = "__all__";

export default function PosPage() {
  const user = useAuthStore((s) => s.user);

  // ── Sucursales: prioriza la asignada al cajero, si no, la primera ──
  const { data: sucursales } = useSucursales();
  const [sucursalId, setSucursalId] = useState<string | undefined>(
    user?.sucursal_id ?? undefined,
  );
  const effectiveSucursalId = sucursalId ?? sucursales?.[0]?.id;

  // ── Catálogo + categorías ─────────────────────────────────────────
  const productosQ  = useProductos(
    effectiveSucursalId ? { sucursal_id: effectiveSucursalId } : undefined,
  );
  const categoriasQ = useCategorias(effectiveSucursalId);

  const [search, setSearch]         = useState("");
  const [categoria, setCategoria]   = useState<string>(ALL_CATEGORIES);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [receiptId, setReceiptId]       = useState<string | null>(null);
  const [activeTab, setActiveTab]       = useState<"catalogo" | "carrito">("catalogo");

  const cart = useCartStore();
  const crearOrden = useCrearOrden();

  const filtered: Producto[] = useMemo(() => {
    if (!productosQ.data) return [];
    const q = search.trim().toLowerCase();
    return productosQ.data.filter((p) => {
      if (!p.activo) return false;
      if (categoria !== ALL_CATEGORIES && p.categoria !== categoria) return false;
      if (!q) return true;
      return (
        p.nombre.toLowerCase().includes(q) ||
        (p.sku ?? "").toLowerCase().includes(q) ||
        p.categoria.toLowerCase().includes(q)
      );
    });
  }, [productosQ.data, search, categoria]);

  const handleAdd = useCallback((p: Producto) => {
    const { items, add } = useCartStore.getState();
    const existing = items.find((i) => i.producto.id === p.id);
    const nextCantidad = (existing?.cantidad ?? 0) + 1;
    if (nextCantidad > p.stock) {
      toast.error(`Stock insuficiente · disponibles ${formatQuantity(p.stock, p.unidad_medida)}`);
      return;
    }
    add(p, 1);
  }, []);

  const handleSetQty = useCallback((productoId: string, qty: number, stock: number, unidad: string) => {
    const { setCantidad } = useCartStore.getState();
    if (qty > stock) {
      toast.error(`Máximo disponible: ${formatQuantity(stock, unidad)}`);
      setCantidad(productoId, stock);
      return;
    }
    setCantidad(productoId, qty);
  }, []);

  // ── Checkout (envía la orden al backend) ──────────────────────────
  async function confirmarCobro() {
    if (!effectiveSucursalId) {
      toast.error("Selecciona una sucursal");
      return;
    }
    if (cart.items.length === 0) return;

    try {
      const payload = {
        sucursal_id:    effectiveSucursalId,
        metodo_pago:    cart.metodo_pago,
        descuento:      cart.descuento,
        domicilio:      cart.domicilio,
        cliente_nombre: cart.cliente || null,
        notas:          cart.notas || null,
        efectivo_recibido:
          cart.metodo_pago === "Efectivo" ? cart.efectivo_recibido : null,
        pagos_mixtos:
          cart.metodo_pago === "Mixto" ? cart.pagos_mixtos : undefined,
        items: cart.items.map((l) => ({
          producto_id:     l.producto.id,
          cantidad:        l.cantidad,
          precio_unitario: l.precio_unitario,
        })),
      };

      if (!syncManager.getOnlineStatus()) {
        const offlineId = await syncManager.queueOrder(payload);
        toast.success("Venta guardada (Modo Offline)");
        setCheckoutOpen(false);
        setReceiptId(offlineId);
        cart.clear();
        setActiveTab("catalogo");
        return;
      }

      const orden = await crearOrden.mutateAsync(payload);
      setCheckoutOpen(false);
      setReceiptId(orden.id);
      cart.clear();
      setActiveTab("catalogo");
    } catch {
      // toast lo dispara el hook
    }
  }

  // ── Render ────────────────────────────────────────────────────────
  const subtotal = cart.subtotal();
  const total    = cart.total();

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col gap-3 p-4 overflow-hidden">
      {/* Selector de pestañas para móvil / tablet */}
      <div className="flex rounded-lg border bg-muted/40 p-1 lg:hidden">
        <button
          type="button"
          onClick={() => setActiveTab("catalogo")}
          className={cn(
            "flex-1 rounded-md py-2 text-sm font-medium transition",
            activeTab === "catalogo"
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          Catálogo
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("carrito")}
          className={cn(
            "flex-1 rounded-md py-2 text-sm font-medium transition flex items-center justify-center gap-1.5",
            activeTab === "carrito"
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <ShoppingCart className="h-4 w-4" />
          <span>Carrito</span>
          {cart.items.length > 0 && (
            <Badge variant="default" className="ml-1 px-1.5 py-0.5 text-[10px]">
              {cart.items.length}
            </Badge>
          )}
        </button>
      </div>

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-[1fr_380px]">
        {/* ── Catálogo ─────────────────────────────────────────── */}
        <section className={cn("flex min-h-0 flex-col", activeTab !== "catalogo" && "hidden lg:flex")}>
          {/* Filtros */}
          <header className="mb-3 flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar producto, SKU, categoría…"
                className="pl-8"
              />
            </div>

            {sucursales && sucursales.length > 1 && (
              <Select value={effectiveSucursalId} onValueChange={setSucursalId}>
                <SelectTrigger className="w-44">
                  <SelectValue placeholder="Sucursal" />
                </SelectTrigger>
                <SelectContent>
                  {sucursales.map((s) => (
                    <SelectItem key={s.id} value={s.id}>{s.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </header>

          {/* Chips de categoría */}
          <div className="mb-3 flex flex-wrap gap-1.5">
            <CategoryChip
              label="Todas"
              active={categoria === ALL_CATEGORIES}
              onClick={() => setCategoria(ALL_CATEGORIES)}
            />
            {(categoriasQ.data ?? []).map((c) => (
              <CategoryChip
                key={c.id}
                label={c.nombre}
                active={categoria === c.nombre}
                onClick={() => setCategoria(c.nombre)}
              />
            ))}
          </div>

          {/* Grid */}
          <div className="flex-1 overflow-y-auto">
            {productosQ.isLoading ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="aspect-[4/3] w-full" />
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-muted-foreground">
                  No hay productos que coincidan.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4 auto-rows-max">
                {filtered.map((p) => (
                  <ProductCard key={p.id} product={p} onSelect={handleAdd} />
                ))}
              </div>
            )}
          </div>
        </section>

        {/* ── Carrito ──────────────────────────────────────────── */}
        <aside className={cn("flex min-h-0 flex-col", activeTab !== "carrito" && "hidden lg:flex")}>
          <Card className="flex flex-1 min-h-0 flex-col overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 border-b py-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <ShoppingCart className="h-5 w-5 text-primary" />
                Carrito
                <Badge variant="secondary" className="ml-1">
                  {cart.items.length}
                </Badge>
              </CardTitle>
              {cart.items.length > 0 && (
                <Button variant="ghost" size="sm" onClick={() => cart.clear()}>
                  Limpiar
                </Button>
              )}
            </CardHeader>

            <CardContent className="flex flex-1 min-h-0 flex-col overflow-hidden p-0">
              <div className="flex-1 overflow-y-auto p-4">
                {cart.items.length === 0 ? (
                  <div className="flex h-full flex-col items-center justify-center text-center">
                    <ShoppingCart className="mb-2 h-10 w-10 text-muted-foreground/30" />
                    <p className="text-sm text-muted-foreground">
                      El carrito está vacío.
                    </p>
                    <p className="text-xs text-muted-foreground/75 mt-1">
                      Haz clic en los productos a la izquierda para agregarlos.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {cart.items.map((item) => (
                      <div
                        key={item.producto.id}
                        className="flex items-center justify-between gap-2 border-b pb-3 last:border-0 last:pb-0"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="truncate text-sm font-medium">
                            {item.producto.nombre}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatCurrency(item.precio_unitario)}
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <QuantityInput
                            value={item.cantidad}
                            onChange={(val) =>
                              handleSetQty(
                                item.producto.id,
                                val,
                                item.producto.stock,
                                item.producto.unidad_medida,
                              )
                            }
                            unidad={item.producto.unidad_medida}
                            max={item.producto.stock}
                            size="sm"
                          />
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:bg-destructive/10"
                            onClick={() => cart.remove(item.producto.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Subtotales y botón Cobrar */}
              <div className="border-t bg-muted/20 p-4 space-y-3">
                {cart.items.length > 0 && (
                  <div className="space-y-1.5 text-sm">
                    {cart.descuento > 0 && (
                      <div className="flex justify-between text-muted-foreground">
                        <span>Subtotal</span>
                        <span>{formatCurrency(subtotal)}</span>
                      </div>
                    )}
                    {cart.descuento > 0 && (
                      <div className="flex justify-between text-destructive">
                        <span>Descuento</span>
                        <span>-{formatCurrency(cart.descuento)}</span>
                      </div>
                    )}
                    <div className="flex justify-between font-bold text-base">
                      <span>Total</span>
                      <span>{formatCurrency(total)}</span>
                    </div>
                  </div>
                )}

                <Button
                  className="w-full"
                  size="lg"
                  disabled={cart.items.length === 0 || crearOrden.isPending}
                  onClick={() => setCheckoutOpen(true)}
                >
                  {crearOrden.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <ReceiptIcon className="mr-2 h-4 w-4" />
                  )}
                  Cobrar {formatCurrency(total)}
                </Button>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>

      {/* Botón flotante para ver carrito (solo móvil/tablet en pestaña catálogo) */}
      {activeTab === "catalogo" && cart.items.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 lg:hidden shadow-xl rounded-full">
          <Button
            onClick={() => setActiveTab("carrito")}
            size="lg"
            className="rounded-full flex items-center gap-2 px-5 py-6 bg-primary text-primary-foreground hover:bg-primary/95 transition-transform active:scale-95"
          >
            <ShoppingCart className="h-5 w-5" />
            <span>Ver Carrito ({cart.items.length})</span>
            <span className="font-bold border-l pl-2 border-primary-foreground/35">{formatCurrency(total)}</span>
          </Button>
        </div>
      )}

      {/* ── Diálogos ──────────────────────────────────────────── */}
      <CheckoutDialog
        open={checkoutOpen}
        onOpenChange={setCheckoutOpen}
        onConfirm={confirmarCobro}
        isPending={crearOrden.isPending}
      />
      <ReceiptDialog
        ordenId={receiptId}
        open={receiptId !== null}
        onOpenChange={(open) => {
          if (!open) setReceiptId(null);
        }}
      />
    </div>
  );
}

function CategoryChip({
  label,
  active,
  onClick,
}: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-card text-muted-foreground hover:border-primary/50 hover:text-foreground"
      }`}
    >
      {label}
    </button>
  );
}
