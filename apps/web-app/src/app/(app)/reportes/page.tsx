"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Banknote, ReceiptText, ShoppingBag, TrendingUp } from "lucide-react";

import {
  useReporteRango,
  useReporteDia,
  useSucursales,
} from "@/lib/hooks/use-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  formatCurrency,
  formatDate,
  formatNumber,
} from "@/lib/formatters";

// Paleta para gráficas (consistente con tokens del tema).
const COLORS = ["#1d4ed8", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#a855f7"];

function isoToday(): string {
  return new Date().toISOString().slice(0, 10);
}
function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export default function ReportesPage() {
  const { data: sucursales } = useSucursales();
  const [sucursalId, setSucursalId] = useState<string | undefined>();
  const effectiveSucursalId = sucursalId ?? sucursales?.[0]?.id;

  const [desde, setDesde] = useState(isoDaysAgo(30));
  const [hasta, setHasta] = useState(isoToday());

  const rangoQ = useReporteRango({
    desde,
    hasta,
    sucursal_id: effectiveSucursalId,
  });
  const diaQ = useReporteDia({
    sucursal_id: effectiveSucursalId ?? "",
    fecha:       hasta,
  });

  const setRange = (days: number) => {
    setHasta(isoToday());
    setDesde(isoDaysAgo(days));
  };

  // Pie chart data → array {name, value}
  const metodosData = useMemo(() => {
    if (!rangoQ.data) return [];
    return Object.entries(rangoQ.data.por_metodo_pago)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [rangoQ.data]);

  return (
    <div className="space-y-4 p-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Reportes</h1>
          <p className="text-sm text-muted-foreground">
            KPIs históricos + cierre de caja del día seleccionado.
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

      {/* Filtros de rango */}
      <Card>
        <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-end sm:gap-4">
          <div className="space-y-1">
            <Label className="text-xs">Desde</Label>
            <Input
              type="date"
              value={desde}
              max={hasta}
              onChange={(e) => setDesde(e.target.value)}
              className="w-44"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Hasta</Label>
            <Input
              type="date"
              value={hasta}
              min={desde}
              max={isoToday()}
              onChange={(e) => setHasta(e.target.value)}
              className="w-44"
            />
          </div>
          <div className="flex flex-1 flex-wrap gap-1.5">
            {[7, 14, 30, 90].map((d) => (
              <Button
                key={d}
                size="sm"
                variant="outline"
                onClick={() => setRange(d)}
                className="h-8"
              >
                Últ. {d}d
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* KPIs del rango */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          icon={Banknote}
          label="Ventas"
          value={rangoQ.data ? formatCurrency(rangoQ.data.total_ventas) : "—"}
          loading={rangoQ.isLoading}
          accent="primary"
        />
        <KpiCard
          icon={ReceiptText}
          label="Órdenes"
          value={rangoQ.data ? formatNumber(rangoQ.data.total_ordenes) : "—"}
          loading={rangoQ.isLoading}
        />
        <KpiCard
          icon={TrendingUp}
          label="Ticket promedio"
          value={rangoQ.data ? formatCurrency(rangoQ.data.ticket_promedio) : "—"}
          loading={rangoQ.isLoading}
        />
        <KpiCard
          icon={ShoppingBag}
          label="Items vendidos"
          value={rangoQ.data ? formatNumber(rangoQ.data.total_items, 1) : "—"}
          loading={rangoQ.isLoading}
        />
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Serie diaria */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Ventas por día</CardTitle>
          </CardHeader>
          <CardContent className="h-72 pt-2">
            {rangoQ.isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : !rangoQ.data || rangoQ.data.serie_diaria.length === 0 ? (
              <EmptyChart label="Sin datos en el rango" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={rangoQ.data.serie_diaria.map((p) => ({
                    fecha: formatDate(p.fecha),
                    Ventas: p.total_ventas,
                    Órdenes: p.total_ordenes,
                  }))}
                  margin={{ top: 5, right: 10, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="fecha" className="text-[10px]" />
                  <YAxis
                    yAxisId="left"
                    className="text-[10px]"
                    tickFormatter={(v) => formatNumber(v / 1000, 0) + "k"}
                  />
                  <YAxis yAxisId="right" orientation="right" className="text-[10px]" />
                  <Tooltip
                    formatter={(v: number, name) =>
                      name === "Ventas" ? formatCurrency(v) : formatNumber(v)
                    }
                  />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="Ventas"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2.5}
                    dot={false}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="Órdenes"
                    stroke="hsl(var(--accent))"
                    strokeWidth={2}
                    strokeDasharray="4 2"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Por método */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pagos por método</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {rangoQ.isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : metodosData.length === 0 ? (
              <EmptyChart label="Sin pagos registrados" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={metodosData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={50}
                    outerRadius={85}
                    paddingAngle={2}
                  >
                    {metodosData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Top productos */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Top productos del rango</CardTitle>
        </CardHeader>
        <CardContent className="h-80 pt-2">
          {rangoQ.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : !rangoQ.data?.top_productos.length ? (
            <EmptyChart label="Sin ventas en el rango" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={rangoQ.data.top_productos.slice(0, 8).map((p) => ({
                  nombre:    p.nombre.length > 18 ? p.nombre.slice(0, 17) + "…" : p.nombre,
                  Ingresos:  p.total,
                  Cantidad:  p.cantidad,
                }))}
                layout="vertical"
                margin={{ top: 5, right: 16, left: 16, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  type="number"
                  className="text-[10px]"
                  tickFormatter={(v) => formatNumber(v / 1000, 0) + "k"}
                />
                <YAxis
                  type="category"
                  dataKey="nombre"
                  width={120}
                  className="text-[10px]"
                />
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
                <Bar dataKey="Ingresos" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Cierre de caja */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Cierre de caja · {formatDate(hasta)}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 p-4">
          {diaQ.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !diaQ.data ? (
            <p className="text-sm text-muted-foreground">Selecciona una sucursal.</p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                <CajaItem label="Total" value={diaQ.data.resumen_caja.total_dia} accent />
                <CajaItem label="Efectivo"      value={diaQ.data.resumen_caja.efectivo} />
                <CajaItem label="Nequi"         value={diaQ.data.resumen_caja.nequi} />
                <CajaItem label="Daviplata"     value={diaQ.data.resumen_caja.daviplata} />
                <CajaItem label="Tarjeta"       value={diaQ.data.resumen_caja.tarjeta} />
                <CajaItem label="Transferencia" value={diaQ.data.resumen_caja.transferencia} />
              </div>

              {diaQ.data.productos.length > 0 ? (
                <div className="overflow-x-auto rounded-md border">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2">Producto</th>
                        <th className="px-3 py-2 text-right">Cantidad</th>
                        <th className="px-3 py-2 text-right">Ingresos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {diaQ.data.productos.map((p, i) => (
                        <tr key={`${p.producto_id ?? i}`} className="border-t">
                          <td className="px-3 py-2 font-medium">{p.producto_nombre}</td>
                          <td className="px-3 py-2 text-right">{formatNumber(p.cantidad_total, 3)}</td>
                          <td className="px-3 py-2 text-right">{formatCurrency(p.total_ingresos)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Sin ventas registradas.</p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function KpiCard({
  icon: Icon,
  label,
  value,
  loading,
  accent,
}: {
  icon: typeof Banknote;
  label: string;
  value: string;
  loading: boolean;
  accent?: "primary";
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className={`rounded-md bg-muted p-2 ${accent === "primary" ? "text-primary" : "text-muted-foreground"}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
          {loading ? (
            <Skeleton className="mt-1 h-6 w-24" />
          ) : (
            <p className="text-xl font-semibold">{value}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function CajaItem({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className={`rounded-md border p-3 ${accent ? "border-primary/40 bg-primary/5" : ""}`}>
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`text-base font-semibold ${accent ? "text-primary" : ""}`}>
        {formatCurrency(value)}
      </p>
    </div>
  );
}

function EmptyChart({ label }: { label: string }) {
  return (
    <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
      {label}
    </div>
  );
}
