"use client";

import Link from "next/link";
import {
  ShoppingCart,
  Receipt,
  AlertTriangle,
  TrendingUp,
  ArrowUpRight,
  Brain,
  Package,
  ChevronRight,
  Sparkles,
  BarChart3,
} from "lucide-react";

import { useReporteDiario, useInventarioAlertas, useSucursales } from "@/lib/hooks/use-api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, formatNumber } from "@/lib/formatters";

interface KpiProps {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  loading?: boolean;
  hint?: string;
  trend?: string;
  accent?: "primary" | "destructive" | "warning" | "success";
}

function KpiCard({ label, value, icon: Icon, loading, hint, trend, accent }: KpiProps) {
  const accentStyles = {
    primary: "border-primary/30 bg-primary/5 text-primary",
    destructive: "border-destructive/30 bg-destructive/5 text-destructive",
    warning: "border-warning/30 bg-warning/5 text-warning-foreground",
    success: "border-success/30 bg-success/5 text-success",
  };

  return (
    <Card className="relative overflow-hidden transition-all hover:shadow-md">
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </CardTitle>
        <div className={`rounded-xl p-2.5 ${accent ? accentStyles[accent] : "bg-muted text-muted-foreground"}`}>
          <Icon className="h-5 w-5" />
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-9 w-28" />
        ) : (
          <div className="text-3xl font-extrabold tracking-tight">{value}</div>
        )}
        <div className="mt-2 flex items-center justify-between text-xs">
          {hint && <span className="text-muted-foreground font-medium">{hint}</span>}
          {trend && (
            <Badge variant="outline" className="text-[10px] font-bold text-success border-success/30 bg-success/10">
              {trend}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: sucursales } = useSucursales();
  const { data: reporte, isLoading: loadingReporte } = useReporteDiario();
  const { data: alertas, isLoading: loadingAlertas } = useInventarioAlertas();

  const lowStockCount = alertas?.length ?? 0;
  const maxProductTotal = reporte?.top_productos?.[0]?.total || 1;

  return (
    <div className="space-y-6 p-6 md:p-8 max-w-7xl mx-auto">
      {/* Header Ejecutivo */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-black tracking-tight">Panel Principal</h1>
            <Badge className="gradient-orion text-white text-xs px-2.5 py-0.5">En Vivo</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Resumen operativo y comercial · {new Date().toLocaleDateString("es-CO", { dateStyle: "full" })}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button asChild variant="outline" size="lg" className="h-12 shadow-sm">
            <Link href="/reportes">
              <BarChart3 className="mr-2 h-5 w-5 text-primary" />
              Ver Reportes
            </Link>
          </Button>
          <Button asChild size="lg" className="h-12 text-base font-bold gradient-orion text-white shadow-lg">
            <Link href="/pos">
              <ShoppingCart className="mr-2 h-5 w-5" />
              Abrir POS
            </Link>
          </Button>
        </div>
      </div>

      {/* Grid de KPIs principales */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Ventas del día"
          value={reporte ? formatCurrency(reporte.total_ventas) : "—"}
          icon={TrendingUp}
          loading={loadingReporte}
          accent="primary"
          hint={reporte?.ticket_promedio ? `Ticket: ${formatCurrency(reporte.ticket_promedio)}` : undefined}
          trend="+100% hoy"
        />
        <KpiCard
          label="Órdenes procesadas"
          value={reporte ? formatNumber(reporte.total_ordenes) : 0}
          icon={Receipt}
          loading={loadingReporte}
          hint="Transacciones cerradas"
        />
        <KpiCard
          label="Unidades vendidas"
          value={reporte ? formatNumber(reporte.total_items, 1) : 0}
          icon={ShoppingCart}
          loading={loadingReporte}
          hint="Productos despachados"
        />
        <KpiCard
          label="Alertas de Inventario"
          value={lowStockCount}
          icon={AlertTriangle}
          loading={loadingAlertas}
          accent={lowStockCount > 0 ? "warning" : "success"}
          hint={lowStockCount === 0 ? "Stock 100% saludable" : "Requiere reabastecimiento"}
        />
      </section>

      {/* Banner de Orion Intelligence Copilot */}
      {lowStockCount > 0 && (
        <Card className="border-warning/30 bg-warning/5 overflow-hidden">
          <CardContent className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 md:p-6">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-warning/20 p-3 text-warning-foreground">
                <Brain className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-bold text-foreground text-base">Orion IA detectó {lowStockCount} productos con stock crítico</h3>
                <p className="text-xs text-muted-foreground">Revisa las sugerencias de compra automática generadas por Machine Learning.</p>
              </div>
            </div>
            <Button asChild size="sm" variant="default" className="gradient-orion shrink-0">
              <Link href="/ml">
                Ver Sugerencias ML
                <ChevronRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Top Productos + Métodos de Pago */}
      <section className="grid gap-6 md:grid-cols-2">
        {/* Top Productos Hoy */}
        <Card className="flex flex-col">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg font-bold">Top Productos de Hoy</CardTitle>
                <CardDescription>Artículos con mayores ingresos</CardDescription>
              </div>
              <Button asChild variant="ghost" size="sm" className="text-xs text-primary">
                <Link href="/reportes">
                  Ver detalle <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex-1">
            {loadingReporte ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full rounded-lg" />
                ))}
              </div>
            ) : reporte && reporte.top_productos.length > 0 ? (
              <div className="space-y-4">
                {reporte.top_productos.slice(0, 5).map((p, i) => {
                  const percentage = Math.round((p.total / maxProductTotal) * 100);
                  return (
                    <div key={p.producto_id ?? i} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                            {i + 1}
                          </span>
                          <span className="font-semibold text-foreground">{p.nombre}</span>
                        </div>
                        <span className="font-bold text-foreground">
                          {formatCurrency(p.total)} ({formatNumber(p.cantidad, 1)} u.)
                        </span>
                      </div>
                      <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full gradient-orion rounded-full transition-all duration-300"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <Package className="h-10 w-10 text-muted-foreground/30 mb-2" />
                <p className="text-sm font-medium text-muted-foreground">Sin ventas registradas hoy</p>
                <p className="text-xs text-muted-foreground">Comienza cobrando en el Punto de Venta.</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Métodos de Pago */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Ventas por Método de Pago</CardTitle>
            <CardDescription>Distribución del flujo de caja de hoy</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col justify-center">
            {loadingReporte ? (
              <div className="grid grid-cols-2 gap-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-lg" />
                ))}
              </div>
            ) : reporte && Object.keys(reporte.por_metodo_pago).length > 0 ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {Object.entries(reporte.por_metodo_pago)
                  .sort(([, a], [, b]) => b - a)
                  .map(([metodo, total]) => (
                    <div key={metodo} className="rounded-xl border p-4 bg-card/50 hover:bg-card transition-colors">
                      <p className="text-xs font-semibold text-muted-foreground uppercase">{metodo}</p>
                      <p className="mt-1 text-lg font-black text-foreground">{formatCurrency(total)}</p>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <Receipt className="h-10 w-10 text-muted-foreground/30 mb-2" />
                <p className="text-sm font-medium text-muted-foreground">No hay pagos procesados hoy</p>
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
