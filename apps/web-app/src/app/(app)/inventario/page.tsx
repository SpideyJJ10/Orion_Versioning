"use client";

import { useState } from "react";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Boxes,
  CircleDollarSign,
  History,
  Package2,
  TrendingDown,
} from "lucide-react";

import {
  useInventarioSummary,
  useInventarioAlertas,
  useMovimientosInventario,
  useSucursales,
} from "@/lib/hooks/use-api";

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { formatCurrency, formatDateTime, formatNumber, formatQuantity } from "@/lib/formatters";
import type { AlertaStock, MovimientoInventario } from "@/lib/api/types";

export default function InventarioPage() {
  const { data: sucursales } = useSucursales();
  const [sucursalId, setSucursalId] = useState<string | undefined>();
  const effectiveSucursalId = sucursalId ?? sucursales?.[0]?.id;

  const summaryQ    = useInventarioSummary(effectiveSucursalId);
  const alertasQ    = useInventarioAlertas(effectiveSucursalId);
  const movimientosQ = useMovimientosInventario(
    effectiveSucursalId ? { sucursal_id: effectiveSucursalId, limit: 50 } : undefined,
  );

  return (
    <div className="space-y-4 p-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Inventario</h1>
          <p className="text-sm text-muted-foreground">
            KPIs en tiempo real, alertas de stock bajo y bitácora de movimientos.
          </p>
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

      {/* KPIs */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          icon={Package2}
          label="Productos"
          value={summaryQ.data ? formatNumber(summaryQ.data.total_productos) : "—"}
          loading={summaryQ.isLoading}
        />
        <KpiCard
          icon={Boxes}
          label="Unidades"
          value={summaryQ.data ? formatNumber(summaryQ.data.total_unidades, 1) : "—"}
          loading={summaryQ.isLoading}
        />
        <KpiCard
          icon={CircleDollarSign}
          label="Valor inventario"
          value={summaryQ.data ? formatCurrency(summaryQ.data.valor_inventario) : "—"}
          loading={summaryQ.isLoading}
          accent="primary"
        />
        <KpiCard
          icon={AlertTriangle}
          label="Sin stock"
          value={summaryQ.data ? formatNumber(summaryQ.data.productos_sin_stock) : "—"}
          loading={summaryQ.isLoading}
          accent={summaryQ.data?.productos_sin_stock ? "destructive" : undefined}
        />
        <KpiCard
          icon={TrendingDown}
          label="Stock bajo"
          value={summaryQ.data ? formatNumber(summaryQ.data.productos_stock_bajo) : "—"}
          loading={summaryQ.isLoading}
          accent={summaryQ.data?.productos_stock_bajo ? "warning" : undefined}
        />
        <KpiCard
          icon={History}
          label="Movimientos 7d"
          value={summaryQ.data ? formatNumber(summaryQ.data.movimientos_ultimos_7d) : "—"}
          loading={summaryQ.isLoading}
        />
      </div>

      {/* Tabs alertas / movimientos */}
      <Tabs defaultValue="alertas" className="space-y-3">
        <TabsList>
          <TabsTrigger value="alertas">
            Alertas
            {alertasQ.data && alertasQ.data.length > 0 && (
              <Badge variant="destructive" className="ml-1.5 h-5 min-w-[20px] justify-center px-1.5 text-[10px]">
                {alertasQ.data.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="movimientos">Movimientos</TabsTrigger>
        </TabsList>

        <TabsContent value="alertas">
          <AlertasTable
            alertas={alertasQ.data ?? []}
            isLoading={alertasQ.isLoading}
          />
        </TabsContent>

        <TabsContent value="movimientos">
          <MovimientosTable
            movimientos={movimientosQ.data ?? []}
            isLoading={movimientosQ.isLoading}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// KPI Card
// ─────────────────────────────────────────────────────────────────────
type KpiAccent = "primary" | "destructive" | "warning";

function KpiCard({
  icon: Icon,
  label,
  value,
  loading,
  accent,
}: {
  icon:    typeof Boxes;
  label:   string;
  value:   string;
  loading: boolean;
  accent?: KpiAccent;
}) {
  const accentClass: Record<KpiAccent, string> = {
    primary:     "text-primary",
    destructive: "text-destructive",
    warning:     "text-warning",
  };
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className={`rounded-md bg-muted p-2 ${accent ? accentClass[accent] : "text-muted-foreground"}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
          {loading ? (
            <Skeleton className="mt-1 h-6 w-20" />
          ) : (
            <p className={`text-xl font-semibold ${accent ? accentClass[accent] : ""}`}>
              {value}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Alertas
// ─────────────────────────────────────────────────────────────────────
function AlertasTable({
  alertas,
  isLoading,
}: { alertas: AlertaStock[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="space-y-2 p-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }
  if (alertas.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-2 p-10 text-center">
          <Boxes className="h-10 w-10 text-success" />
          <p className="text-sm font-medium">Inventario saludable</p>
          <p className="text-xs text-muted-foreground">
            No hay productos por debajo del umbral mínimo.
          </p>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Productos por reabastecer</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-2">Producto</th>
              <th className="px-4 py-2">Sucursal</th>
              <th className="px-4 py-2 text-right">Stock</th>
              <th className="px-4 py-2 text-right">Mínimo</th>
              <th className="px-4 py-2">Severidad</th>
            </tr>
          </thead>
          <tbody>
            {alertas.map((a) => (
              <tr key={a.producto_id} className="border-t">
                <td className="px-4 py-2 font-medium">{a.producto_nombre}</td>
                <td className="px-4 py-2 text-muted-foreground">
                  {a.sucursal_nombre || "—"}
                </td>
                <td className="px-4 py-2 text-right">
                  {formatQuantity(a.stock, a.unidad_medida)}
                </td>
                <td className="px-4 py-2 text-right text-muted-foreground">
                  {formatQuantity(a.stock_minimo, a.unidad_medida)}
                </td>
                <td className="px-4 py-2">
                  <SeverityBadge severidad={a.severidad} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function SeverityBadge({ severidad }: { severidad: string }) {
  if (severidad === "agotado") {
    return <Badge variant="destructive">Agotado</Badge>;
  }
  if (severidad === "critical") {
    return <Badge className="bg-destructive/15 text-destructive hover:bg-destructive/20">Crítico</Badge>;
  }
  return <Badge className="bg-warning text-warning-foreground hover:bg-warning/90">Bajo</Badge>;
}

// ─────────────────────────────────────────────────────────────────────
// Movimientos
// ─────────────────────────────────────────────────────────────────────
function MovimientosTable({
  movimientos,
  isLoading,
}: { movimientos: MovimientoInventario[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="space-y-2 p-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }
  if (movimientos.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-2 p-10 text-center">
          <History className="h-10 w-10 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">
            Aún no se han registrado movimientos.
          </p>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-2">Fecha</th>
              <th className="px-4 py-2">Producto</th>
              <th className="px-4 py-2">Tipo</th>
              <th className="px-4 py-2 text-right">Cantidad</th>
              <th className="px-4 py-2 text-right">Stock final</th>
              <th className="px-4 py-2">Motivo</th>
            </tr>
          </thead>
          <tbody>
            {movimientos.map((m) => {
              const isIn = m.cantidad > 0;
              return (
                <tr key={m.id} className="border-t">
                  <td className="px-4 py-2 text-muted-foreground">
                    {formatDateTime(m.fecha)}
                  </td>
                  <td className="px-4 py-2 font-medium">
                    {/* product name not in payload — fallback */}
                    <span className="font-mono text-xs text-muted-foreground">
                      {m.producto_id.slice(0, 8)}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${
                      isIn
                        ? "bg-success/15 text-success"
                        : "bg-destructive/15 text-destructive"
                    }`}>
                      {isIn ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                      {m.tipo}
                    </span>
                  </td>
                  <td className={`px-4 py-2 text-right font-medium ${
                    isIn ? "text-success" : "text-destructive"
                  }`}>
                    {isIn ? "+" : ""}{formatNumber(m.cantidad, 3)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {formatNumber(m.stock_despues, 3)}
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {m.motivo || "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
