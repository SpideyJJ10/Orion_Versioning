"use client";

import Link from "next/link";
import {
  ShoppingCart,
  Receipt,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";

import { useReporteDiario, useInventarioAlertas, useSucursales } from "@/lib/hooks/use-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { formatCurrency, formatNumber } from "@/lib/formatters";

interface KpiProps {
  label:    string;
  value:    string | number;
  icon:     React.ComponentType<{ className?: string }>;
  loading?: boolean;
  hint?:    string;
  accent?:  "primary" | "destructive" | "warning";
}

function Kpi({ label, value, icon: Icon, loading, hint, accent }: KpiProps) {
  const accentIcon = {
    primary:     "text-primary",
    destructive: "text-destructive",
    warning:     "text-warning",
  };
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <div className={`rounded-md bg-muted p-1.5 ${accent ? accentIcon[accent] : "text-muted-foreground"}`}>
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <div className={`text-2xl font-bold ${accent ? accentIcon[accent] : ""}`}>{value}</div>
        )}
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: sucursales } = useSucursales();
  const { data: reporte, isLoading: loadingReporte } = useReporteDiario();
  const { data: alertas, isLoading: loadingAlertas } = useInventarioAlertas();

  const lowStockCount = alertas?.length ?? 0;

  return (
    <div className="space-y-6 p-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Resumen del día · {new Date().toLocaleDateString("es-CO", { dateStyle: "full" })}
        </p>
      </header>

      {/* KPIs */}
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Kpi
          label="Ventas de hoy"
          value={reporte ? formatCurrency(reporte.total_ventas) : "—"}
          icon={TrendingUp}
          loading={loadingReporte}
          accent="primary"
          hint={
            reporte?.ticket_promedio
              ? `Ticket: ${formatCurrency(reporte.ticket_promedio)}`
              : undefined
          }
        />
        <Kpi
          label="Órdenes de hoy"
          value={reporte ? formatNumber(reporte.total_ordenes) : 0}
          icon={Receipt}
          loading={loadingReporte}
        />
        <Kpi
          label="Items vendidos"
          value={reporte ? formatNumber(reporte.total_items, 1) : 0}
          icon={ShoppingCart}
          loading={loadingReporte}
        />
        <Kpi
          label="Alertas de stock"
          value={lowStockCount}
          icon={AlertTriangle}
          loading={loadingAlertas}
          accent={lowStockCount > 0 ? "warning" : undefined}
          hint={lowStockCount === 0 ? "Inventario saludable" : "Revisar inventario"}
        />
      </section>

      {/* Bottom: top productos + acciones rápidas */}
      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top productos hoy</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingReporte ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : reporte && reporte.top_productos.length > 0 ? (
              <ul className="space-y-2">
                {reporte.top_productos.slice(0, 5).map((p, i) => (
                  <li
                    key={p.producto_id ?? i}
                    className="flex items-center justify-between text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
                        {i + 1}
                      </span>
                      <span className="truncate">{p.nombre}</span>
                    </div>
                    <span className="shrink-0 font-medium">
                      {formatNumber(p.cantidad, 1)}× · {formatCurrency(p.total)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-4 text-center text-sm text-muted-foreground">
                Sin ventas registradas hoy.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Acciones rápidas</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Button asChild>
              <Link href="/pos">
                <ShoppingCart className="mr-2 h-4 w-4" />
                Abrir POS
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/productos">Gestionar productos</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/inventario">Ver inventario</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/reportes">Ver reportes</Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Métodos de pago del día */}
      {reporte && Object.keys(reporte.por_metodo_pago).length > 0 && (
        <section>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Ingresos por método de pago (hoy)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                {Object.entries(reporte.por_metodo_pago)
                  .sort(([, a], [, b]) => b - a)
                  .map(([metodo, total]) => (
                    <div key={metodo} className="rounded-md border p-3">
                      <p className="text-xs text-muted-foreground">{metodo}</p>
                      <p className="mt-0.5 font-semibold">{formatCurrency(total)}</p>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  );
}
