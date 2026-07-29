"use client";

import { useMemo, useState } from "react";
import { Pencil, Plus, Search, Trash2, Boxes } from "lucide-react";

import {
  useProductos,
  useSucursales,
  useEliminarProducto,
} from "@/lib/hooks/use-api";

import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { ProductoFormDialog } from "@/components/productos/producto-form-dialog";
import { AjusteStockDialog } from "@/components/productos/ajuste-stock-dialog";
import { useAuthStore } from "@/lib/stores/auth-store";
import { formatCurrency, formatQuantity } from "@/lib/formatters";
import type { Producto } from "@/lib/api/types";

export default function ProductosPage() {
  const user = useAuthStore((s) => s.user);
  const canMutate = user
    ? ["owner", "manager", "inventario", "super_admin"].includes(user.rol)
    : false;

  const { data: sucursales } = useSucursales();
  const [sucursalId, setSucursalId] = useState<string | undefined>();
  const effectiveSucursalId = sucursalId ?? sucursales?.[0]?.id;

  const [search, setSearch] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);

  const productosQ = useProductos(
    effectiveSucursalId
      ? {
          sucursal_id:        effectiveSucursalId,
          search:             search || undefined,
          incluir_inactivos:  includeInactive || undefined,
        }
      : undefined,
  );
  const eliminarM = useEliminarProducto();

  // Diálogos
  const [editing,  setEditing]  = useState<Producto | null>(null);
  const [creating, setCreating] = useState(false);
  const [ajusting, setAjusting] = useState<Producto | null>(null);

  const productos = productosQ.data ?? [];
  const counts = useMemo(() => ({
    total:  productos.length,
    sin:    productos.filter((p) => p.stock <= 0).length,
    bajo:   productos.filter((p) => p.stock > 0 && p.stock <= p.stock_minimo).length,
  }), [productos]);

  async function handleDelete(p: Producto) {
    if (!confirm(`¿Desactivar "${p.nombre}"? Podrás reactivarlo luego.`)) return;
    try {
      await eliminarM.mutateAsync(p.id);
    } catch {
      /* toast en hook */
    }
  }

  if (!effectiveSucursalId) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            No hay sucursales disponibles para este negocio.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6">
      {/* Header */}
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Productos</h1>
          <p className="text-sm text-muted-foreground">
            Catálogo del negocio · {counts.total} {counts.total === 1 ? "producto" : "productos"}
            {counts.sin > 0 && (
              <> · <span className="text-destructive">{counts.sin} sin stock</span></>
            )}
            {counts.bajo > 0 && (
              <> · <span className="text-warning">{counts.bajo} bajo mínimo</span></>
            )}
          </p>
        </div>
        {canMutate && (
          <Button onClick={() => setCreating(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Nuevo producto
          </Button>
        )}
      </header>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre, SKU o categoría…"
            className="pl-8"
          />
        </div>
        {sucursales && sucursales.length > 1 && (
          <Select value={effectiveSucursalId} onValueChange={setSucursalId}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {sucursales.map((s) => (
                <SelectItem key={s.id} value={s.id}>{s.nombre}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
            className="h-4 w-4 accent-primary"
          />
          Incluir inactivos
        </label>
      </div>

      {/* Lista */}
      {productosQ.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : productos.length === 0 ? (
        <Card>
          <CardContent className="space-y-3 p-10 text-center">
            <Boxes className="mx-auto h-10 w-10 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              No hay productos {search ? "que coincidan con tu búsqueda." : "en este catálogo."}
            </p>
            {canMutate && !search && (
              <Button onClick={() => setCreating(true)} variant="outline">
                <Plus className="mr-2 h-4 w-4" />
                Crear el primero
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3">Nombre</th>
                    <th className="px-4 py-3">Categoría</th>
                    <th className="px-4 py-3">SKU</th>
                    <th className="px-4 py-3 text-right">Precio</th>
                    <th className="px-4 py-3 text-right">Stock</th>
                    <th className="px-4 py-3">Estado</th>
                    {canMutate && <th className="px-4 py-3 text-right">Acciones</th>}
                  </tr>
                </thead>
                <tbody>
                  {productos.map((p) => (
                    <tr
                      key={p.id}
                      className="border-t transition-colors hover:bg-muted/30"
                    >
                      <td className="px-4 py-3 font-medium">
                        <div className="flex items-center gap-2">
                          {p.imagen_url ? (
                            /* eslint-disable-next-line @next/next/no-img-element */
                            <img
                              src={p.imagen_url}
                              alt=""
                              className="h-8 w-8 rounded object-cover"
                            />
                          ) : (
                            <div className="flex h-8 w-8 items-center justify-center rounded bg-muted">
                              <Boxes className="h-3.5 w-3.5 text-muted-foreground/50" />
                            </div>
                          )}
                          <div className="min-w-0">
                            <div className="truncate">{p.nombre}</div>
                            {!p.activo && (
                              <span className="text-[10px] uppercase text-muted-foreground">
                                Inactivo
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {p.categoria || "—"}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {p.sku || "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-medium">
                        {formatCurrency(p.precio)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatQuantity(p.stock, p.unidad_medida)}
                      </td>
                      <td className="px-4 py-3">
                        {p.stock <= 0 ? (
                          <Badge variant="destructive">Agotado</Badge>
                        ) : p.stock <= p.stock_minimo ? (
                          <Badge className="bg-warning text-warning-foreground hover:bg-warning/90">
                            Bajo
                          </Badge>
                        ) : (
                          <Badge variant="outline">OK</Badge>
                        )}
                      </td>
                      {canMutate && (
                        <td className="px-4 py-3">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setAjusting(p)}
                              title="Ajustar stock"
                            >
                              <Boxes className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setEditing(p)}
                              title="Editar"
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(p)}
                              title="Desactivar"
                              className="text-muted-foreground hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Diálogos */}
      <ProductoFormDialog
        open={creating}
        onOpenChange={setCreating}
        sucursalId={effectiveSucursalId}
      />
      <ProductoFormDialog
        open={!!editing}
        onOpenChange={(open) => !open && setEditing(null)}
        producto={editing}
        sucursalId={effectiveSucursalId}
      />
      <AjusteStockDialog
        open={!!ajusting}
        onOpenChange={(open) => !open && setAjusting(null)}
        producto={ajusting}
      />
    </div>
  );
}
