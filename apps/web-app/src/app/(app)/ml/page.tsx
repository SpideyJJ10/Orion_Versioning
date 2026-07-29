"use client";

import { useState } from "react";
import {
  Brain,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Loader2,
  ShoppingCart,
  Zap,
} from "lucide-react";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";

import {
  useMlStatus,
  useTrainMl,
  useMlAlertas,
  useAcknowledgeMlAlerta,
  useMlRestockSuggestions,
  useMlForecast,
  useProductos,
  useSucursales,
} from "@/lib/hooks/use-api";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { formatCurrency, formatDateTime, formatNumber, formatQuantity } from "@/lib/formatters";
import { useAuthStore } from "@/lib/stores/auth-store";
import type { MlAlerta, RestockSuggestion } from "@/lib/api/types";

const URGENCY_COLORS: Record<string, string> = {
  critica: "bg-destructive text-destructive-foreground",
  alta:    "bg-orange-500 text-white",
  media:   "bg-warning text-warning-foreground",
  baja:    "bg-muted text-muted-foreground",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-destructive/15 text-destructive border-destructive/20",
  warning:  "bg-warning/15 text-warning-foreground border-warning/20",
  info:     "bg-primary/10 text-primary border-primary/20",
};

export default function MlPage() {
  const user       = useAuthStore((s) => s.user);
  const canTrain   = user ? ["owner", "manager", "super_admin"].includes(user.rol) : false;

  const statusQ    = useMlStatus();
  const trainM     = useTrainMl();
  const alertasQ   = useMlAlertas({ incluir_leidas: false });
  const ackM       = useAcknowledgeMlAlerta();
  const restockQ   = useMlRestockSuggestions();

  const { data: sucursales } = useSucursales();
  const [sucursalId, setSucursalId] = useState<string | undefined>();
  const effectiveSucursalId = sucursalId ?? sucursales?.[0]?.id;

  const productosQ = useProductos(
    effectiveSucursalId ? { sucursal_id: effectiveSucursalId } : undefined,
  );
  const [selectedProductoId, setSelectedProductoId] = useState<string | undefined>();
  const forecastQ = useMlForecast(selectedProductoId);

  return (
    <div className="space-y-4 p-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Inteligencia Artificial</h1>
          <p className="text-sm text-muted-foreground">
            Predicciones de demanda, alertas ML y sugerencias de reabastecimiento.
          </p>
        </div>
        {canTrain && (
          <Button
            onClick={() => trainM.mutate(undefined)}
            disabled={trainM.isPending}
            size="sm"
          >
            {trainM.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Brain className="mr-2 h-4 w-4" />
            )}
            Entrenar modelos
          </Button>
        )}
      </header>

      {/* Status Cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatusKpi
          icon={Brain}
          label="Motor ML"
          value={
            statusQ.isLoading
              ? "—"
              : statusQ.data?.prophet_disponible
              ? "Prophet activo"
              : "Baseline activo"
          }
          loading={statusQ.isLoading}
          accent={statusQ.data?.prophet_disponible ? "success" : undefined}
        />
        <StatusKpi
          icon={TrendingUp}
          label="Modelos entrenados"
          value={statusQ.data ? formatNumber(statusQ.data.modelos_entrenados) : "—"}
          loading={statusQ.isLoading}
        />
        <StatusKpi
          icon={AlertTriangle}
          label="Alertas activas"
          value={statusQ.data ? formatNumber(statusQ.data.alertas_no_leidas) : "—"}
          loading={statusQ.isLoading}
          accent={statusQ.data?.alertas_no_leidas ? "warning" : undefined}
        />
        <StatusKpi
          icon={RefreshCw}
          label="RMSE promedio"
          value={
            statusQ.data?.rmse_promedio != null
              ? formatNumber(statusQ.data.rmse_promedio, 3)
              : "Sin datos"
          }
          loading={statusQ.isLoading}
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="alertas" className="space-y-3">
        <TabsList>
          <TabsTrigger value="alertas">
            Alertas inteligentes
            {alertasQ.data && alertasQ.data.length > 0 && (
              <Badge variant="destructive" className="ml-1.5 h-5 min-w-[20px] justify-center px-1.5 text-[10px]">
                {alertasQ.data.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="restock">Reabastecimiento</TabsTrigger>
          <TabsTrigger value="forecast">Pronóstico</TabsTrigger>
        </TabsList>

        {/* Alertas ML */}
        <TabsContent value="alertas">
          <AlertasMLPanel
            alertas={alertasQ.data ?? []}
            isLoading={alertasQ.isLoading}
            onAck={(id) => ackM.mutate(id)}
            isAcking={ackM.isPending}
          />
        </TabsContent>

        {/* Restock */}
        <TabsContent value="restock">
          <RestockPanel
            items={restockQ.data ?? []}
            isLoading={restockQ.isLoading}
          />
        </TabsContent>

        {/* Forecast */}
        <TabsContent value="forecast" className="space-y-3">
          <Card>
            <CardContent className="flex flex-wrap items-center gap-3 p-4">
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
              <Select value={selectedProductoId} onValueChange={setSelectedProductoId}>
                <SelectTrigger className="w-56">
                  <SelectValue placeholder="Seleccionar producto…" />
                </SelectTrigger>
                <SelectContent>
                  {(productosQ.data ?? []).map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {!selectedProductoId ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 p-12 text-center">
                <TrendingUp className="h-12 w-12 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">
                  Selecciona un producto para ver su pronóstico de demanda.
                </p>
              </CardContent>
            </Card>
          ) : forecastQ.isLoading ? (
            <Card>
              <CardContent className="p-4">
                <Skeleton className="h-72 w-full" />
              </CardContent>
            </Card>
          ) : !forecastQ.data ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 p-12 text-center">
                <Brain className="h-12 w-12 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">
                  No hay pronóstico disponible para este producto. Entrena los modelos primero.
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Pronóstico: {forecastQ.data.producto_nombre}
                  <Badge variant="outline" className="ml-auto text-xs">
                    {forecastQ.data.modelo_tipo}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={forecastQ.data.puntos.map((p) => ({
                      fecha:     p.fecha,
                      demanda:   p.demanda,
                      inf:       p.intervalo_inf,
                      sup:       p.intervalo_sup,
                    }))}
                    margin={{ top: 5, right: 10, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="fecha" className="text-[10px]" />
                    <YAxis className="text-[10px]" />
                    <Tooltip
                      formatter={(v: number) => [formatNumber(v, 2), "Demanda"]}
                    />
                    <Area
                      type="monotone"
                      dataKey="sup"
                      stroke="transparent"
                      fill="hsl(var(--primary) / 0.1)"
                    />
                    <Area
                      type="monotone"
                      dataKey="inf"
                      stroke="transparent"
                      fill="hsl(var(--background))"
                    />
                    <Area
                      type="monotone"
                      dataKey="demanda"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2.5}
                      fill="transparent"
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Status KPI ─────────────────────────────────────────────────────────────
function StatusKpi({
  icon: Icon,
  label,
  value,
  loading,
  accent,
}: {
  icon: typeof Brain;
  label: string;
  value: string;
  loading: boolean;
  accent?: "success" | "warning";
}) {
  const accentClass = {
    success: "text-green-600 dark:text-green-400",
    warning: "text-warning",
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
            <Skeleton className="mt-1 h-5 w-24" />
          ) : (
            <p className={`text-base font-semibold ${accent ? accentClass[accent] : ""}`}>
              {value}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Alertas ML ─────────────────────────────────────────────────────────────
function AlertasMLPanel({
  alertas,
  isLoading,
  onAck,
  isAcking,
}: {
  alertas:   MlAlerta[];
  isLoading: boolean;
  onAck:     (id: number) => void;
  isAcking:  boolean;
}) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="space-y-2 p-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }
  if (alertas.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 p-12 text-center">
          <CheckCircle2 className="h-12 w-12 text-green-500" />
          <p className="text-sm font-medium">Sin alertas activas</p>
          <p className="text-xs text-muted-foreground">
            El sistema no detectó anomalías en este momento.
          </p>
        </CardContent>
      </Card>
    );
  }
  return (
    <div className="space-y-2">
      {alertas.map((a) => (
        <Card key={a.id} className={`border ${SEVERITY_COLORS[a.severidad] ?? ""}`}>
          <CardContent className="flex items-start gap-3 p-4">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold">{a.titulo}</p>
                <Badge variant="outline" className="text-[10px]">{a.tipo}</Badge>
              </div>
              <p className="mt-0.5 text-xs">{a.mensaje}</p>
              {a.recomendacion && (
                <p className="mt-1 text-xs italic text-muted-foreground">
                  💡 {a.recomendacion}
                </p>
              )}
              <p className="mt-1 text-[10px] text-muted-foreground">
                {formatDateTime(a.creada_en)}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onAck(a.id)}
              disabled={isAcking}
              className="shrink-0"
            >
              <CheckCircle2 className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ─── Restock Panel ──────────────────────────────────────────────────────────
function RestockPanel({
  items,
  isLoading,
}: {
  items:     RestockSuggestion[];
  isLoading: boolean;
}) {
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
  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 p-12 text-center">
          <ShoppingCart className="h-12 w-12 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">
            No hay sugerencias de reabastecimiento disponibles.
          </p>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Producto</th>
                <th className="px-4 py-3">Sucursal</th>
                <th className="px-4 py-3 text-right">Stock actual</th>
                <th className="px-4 py-3 text-right">Demanda (proyect.)</th>
                <th className="px-4 py-3 text-right">Días cobertura</th>
                <th className="px-4 py-3 text-right">Cantidad sugerida</th>
                <th className="px-4 py-3">Urgencia</th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={`${s.producto_id}-${s.sucursal_id}`} className="border-t">
                  <td className="px-4 py-3 font-medium">{s.producto_nombre}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {s.sucursal_nombre || "—"}
                  </td>
                  <td className="px-4 py-3 text-right">{formatNumber(s.stock_actual, 2)}</td>
                  <td className="px-4 py-3 text-right">{formatNumber(s.demanda_proyectada, 2)}</td>
                  <td className="px-4 py-3 text-right">
                    {s.dias_cobertura != null ? formatNumber(s.dias_cobertura, 1) + " días" : "—"}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-primary">
                    {formatNumber(s.cantidad_sugerida, 2)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${URGENCY_COLORS[s.urgencia] ?? "bg-muted"}`}>
                      <Zap className="h-3 w-3" />
                      {s.urgencia}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
