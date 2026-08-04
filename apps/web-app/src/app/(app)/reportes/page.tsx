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
  Area,
  AreaChart,
} from "recharts";
import {
  Banknote,
  ReceiptText,
  ShoppingBag,
  TrendingUp,
  Calendar,
  Building2,
  Printer,
  Download,
  Filter,
} from "lucide-react";

import {
  useReporteRango,
  useReporteDia,
  useSucursales,
} from "@/lib/hooks/use-api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

const COLORS = ["#7c3aed", "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#ec4899"];

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
  const [activeDays, setActiveDays] = useState<number>(30);

  const rangoQ = useReporteRango({
    desde,
    hasta,
    sucursal_id: effectiveSucursalId,
  });

  const diaQ = useReporteDia({
    sucursal_id: effectiveSucursalId ?? "",
    fecha: hasta,
  });

  const setRange = (days: number) => {
    setActiveDays(days);
    setHasta(isoToday());
    setDesde(isoDaysAgo(days));
  };

  const metodosData = useMemo(() => {
    if (!rangoQ.data) return [];
    return Object.entries(rangoQ.data.por_metodo_pago)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [rangoQ.data]);

  return (
    <div className="space-y-6 p-6 md:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b pb-5">
        <div>
          <h1 className="text-3xl font-black tracking-tight">Reportes & Cierre</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Análisis de rendimiento comercial y control financiero.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {sucursales && sucursales.length > 1 && (
            <Select value={effectiveSucursalId} onValueChange={setSucursalId}>
              <SelectTrigger className="w-48 h-11">
                <Building2 className="mr-2 h-4 w-4 text-muted-foreground" />
                <SelectValue placeholder="Sucursal" />
              </SelectTrigger>
              <SelectContent>
                {sucursales.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.nombre}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <Button variant="outline" size="lg" className="h-11" onClick={() => window.print()}>
            <Printer className="mr-2 h-4 w-4" />
            Imprimir
          </Button>
        </div>
      </header>

      {/* Rango de Fechas & Filtros Rápido */}
      <Card>
        <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <div className="space-y-1">
              <Label className="text-xs font-semibold text-muted-foreground">Desde</Label>
              <Input
                type="date"
                value={desde}
                max={hasta}
                onChange={(e) => {
                  setDesde(e.target.value);
                  setActiveDays(0);
                }}
                className="w-40 h-10 font-medium"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs font-semibold text-muted-foreground">Hasta</Label>
              <Input
                type="date"
                value={hasta}
                min={desde}
                max={isoToday()}
                onChange={(e) => {
                  setHasta(e.target.value);
                  setActiveDays(0);
                }}
                className="w-40 h-10 font-medium"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {[7, 14, 30, 90].map((d) => (
              <Button
                key={d}
                size="sm"
                variant={activeDays === d ? "default" : "outline"}
                onClick={() => setRange(d)}
                className={`h-9 px-3 text-xs font-bold ${activeDays === d ? "gradient-orion text-white" : ""}`}
              >
                {d} Días
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* KPIs del Rango */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          icon={Banknote}
          label="Total Ventas"
          value={rangoQ.data ? formatCurrency(rangoQ.data.total_ventas) : "—"}
          loading={rangoQ.isLoading}
          accent="primary"
        />
        <KpiCard
          icon={ReceiptText}
          label="Total Órdenes"
          value={rangoQ.data ? formatNumber(rangoQ.data.total_ordenes) : "—"}
          loading={rangoQ.isLoading}
        />
        <KpiCard
          icon={TrendingUp}
          label="Ticket Promedio"
          value={rangoQ.data ? formatCurrency(rangoQ.data.ticket_promedio) : "—"}
          loading={rangoQ.isLoading}
        />
        <KpiCard
          icon={ShoppingBag}
          label="Items Despachados"
          value={rangoQ.data ? formatNumber(rangoQ.data.total_items, 1) : "—"}
          loading={rangoQ.isLoading}
        />
      </div>

      {/* Gráficos de Tendencia & Pagos */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Serie Diaria */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Evolución de Ventas</CardTitle>
            <CardDescription>Ingresos vs Órdenes en el período seleccionado</CardDescription>
          </CardHeader>
          <CardContent className="h-80 pt-2">
            {rangoQ.isLoading ? (
              <Skeleton className="h-full w-full rounded-xl" />
            ) : !rangoQ.data || rangoQ.data.serie_diaria.length === 0 ? (
              <EmptyState label="Sin datos en el rango seleccionado" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={rangoQ.data.serie_diaria.map((p) => ({
                    fecha: formatDate(p.fecha),
                    Ventas: p.total_ventas,
                    Órdenes: p.total_ordenes,
                  }))}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="ventasGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="fecha" className="text-xs" />
                  <YAxis className="text-xs" tickFormatter={(v) => formatNumber(v / 1000, 0) + "k"} />
                  <Tooltip
                    formatter={(v: number, name) =>
                      name === "Ventas" ? formatCurrency(v) : formatNumber(v)
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="Ventas"
                    stroke="hsl(var(--primary))"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#ventasGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Métodos de Pago */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-bold">Distribución de Pagos</CardTitle>
            <CardDescription>Participación por canal de cobro</CardDescription>
          </CardHeader>
          <CardContent className="h-80">
            {rangoQ.isLoading ? (
              <Skeleton className="h-full w-full rounded-xl" />
            ) : metodosData.length === 0 ? (
              <EmptyState label="Sin pagos registrados" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={metodosData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={4}
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

      {/* Top Productos del Rango */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-bold">Top Productos por Ventas</CardTitle>
          <CardDescription>Los artículos con mayor generación de ingresos</CardDescription>
        </CardHeader>
        <CardContent className="h-80 pt-2">
          {rangoQ.isLoading ? (
            <Skeleton className="h-full w-full rounded-xl" />
          ) : !rangoQ.data?.top_productos.length ? (
            <EmptyState label="Sin ventas registradas en el rango" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={rangoQ.data.top_productos.slice(0, 8).map((p) => ({
                  nombre: p.nombre.length > 20 ? p.nombre.slice(0, 19) + "…" : p.nombre,
                  Ingresos: p.total,
                  Cantidad: p.cantidad,
                }))}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis type="number" className="text-xs" tickFormatter={(v) => formatNumber(v / 1000, 0) + "k"} />
                <YAxis type="category" dataKey="nombre" width={130} className="text-xs font-semibold" />
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
                <Bar dataKey="Ingresos" fill="hsl(var(--primary))" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Cierre de Caja del Día */}
      <Card id="orion-print-area">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl font-black">Cierre de Caja del Día</CardTitle>
              <CardDescription>Resumen financiero al {formatDate(hasta)}</CardDescription>
            </div>
            <Badge variant="outline" className="text-xs font-bold border-primary text-primary">
              Cierre Cuadrado
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {diaQ.isLoading ? (
            <Skeleton className="h-40 w-full rounded-xl" />
          ) : !diaQ.data ? (
            <p className="text-sm text-muted-foreground">Selecciona una sucursal para ver el cierre.</p>
          ) : (
            <>
              {/* Tarjetas de método */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <CajaCard label="Total Día" value={diaQ.data.resumen_caja.total_dia} accent />
                <CajaCard label="Efectivo" value={diaQ.data.resumen_caja.efectivo} />
                <CajaCard label="Nequi" value={diaQ.data.resumen_caja.nequi} />
                <CajaCard label="Daviplata" value={diaQ.data.resumen_caja.daviplata} />
                <CajaCard label="Tarjeta" value={diaQ.data.resumen_caja.tarjeta} />
                <CajaCard label="Transferencia" value={diaQ.data.resumen_caja.transferencia} />
              </div>

              {/* Detalle por producto */}
              {diaQ.data.productos.length > 0 ? (
                <div className="overflow-x-auto rounded-xl border">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3">Producto</th>
                        <th className="px-4 py-3 text-right">Cantidad Vendida</th>
                        <th className="px-4 py-3 text-right">Total Ingresos</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {diaQ.data.productos.map((p, i) => (
                        <tr key={`${p.producto_id ?? i}`} className="hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-3 font-semibold text-foreground">{p.producto_nombre}</td>
                          <td className="px-4 py-3 text-right font-medium">{formatNumber(p.cantidad_total, 3)} u.</td>
                          <td className="px-4 py-3 text-right font-bold text-primary">{formatCurrency(p.total_ingresos)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Sin ventas registradas en esta fecha.</p>
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
    <Card className="transition-all hover:shadow-md">
      <CardContent className="flex items-center gap-4 p-5">
        <div className={`rounded-xl p-3 ${accent === "primary" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</p>
          {loading ? (
            <Skeleton className="mt-1 h-7 w-28" />
          ) : (
            <p className="text-2xl font-black tracking-tight">{value}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function CajaCard({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 transition-all ${accent ? "border-primary bg-primary/5 shadow-sm" : "bg-card"}`}>
      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={`text-lg font-black mt-1 ${accent ? "text-primary" : "text-foreground"}`}>
        {formatCurrency(value)}
      </p>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex h-full items-center justify-center text-sm font-medium text-muted-foreground">
      {label}
    </div>
  );
}
