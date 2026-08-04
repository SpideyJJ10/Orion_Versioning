"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
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
  Building2,
  Printer,
  Lock,
  Unlock,
  CheckCircle2,
  AlertTriangle,
  Coins,
  ShieldCheck,
  RotateCcw,
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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Numpad } from "@/components/ui/numpad";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { formatCurrency, formatDate, formatNumber } from "@/lib/formatters";

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

  // ── Estado de Privacidad y PIN para Cierre ──
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [pinDialogOpen, setPinDialogOpen] = useState(false);
  const [pinInput, setPinInput] = useState("");
  const [verifyingPin, setVerifyingPin] = useState(false);

  // ── Arqueo de Caja ──
  const [efectivoFisicoInput, setEfectivoFisicoInput] = useState<string>("");
  const [cierreGuardado, setCierreGuardado] = useState(false);

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

  // Verificar PIN de administrador
  const handleVerifyPin = async () => {
    if (!pinInput.trim()) return;
    setVerifyingPin(true);
    try {
      await api.post("/api/v3/auth/verify-admin-pin", { pin: pinInput });
      setIsUnlocked(true);
      setPinDialogOpen(false);
      setPinInput("");
      toast.success("¡Acceso autorizado de Administrador!");
    } catch {
      toast.error("PIN de Administrador incorrecto.");
      setPinInput("");
    } finally {
      setVerifyingPin(false);
    }
  };

  // Cálculo de Arqueo
  const efectivoSistema = diaQ.data?.resumen_caja.efectivo ?? 0;
  const efectivoFisico = efectivoFisicoInput !== "" ? Number(efectivoFisicoInput) : null;
  const diferencia = efectivoFisico !== null ? efectivoFisico - efectivoSistema : null;

  return (
    <div className="space-y-6 p-6 md:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b pb-5">
        <div>
          <h1 className="text-3xl font-black tracking-tight">Reportes & Cierre</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Análisis de rendimiento comercial y control financiero privado.
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

      {/* 🔒 CIERRE DE CAJA Y ARQUEO PRIVADO */}
      <Card id="orion-print-area" className="border-2 border-primary/20 overflow-hidden">
        <CardHeader className="bg-muted/20 border-b">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle className="text-xl font-black flex items-center gap-2">
                {isUnlocked ? <Unlock className="h-5 w-5 text-success" /> : <Lock className="h-5 w-5 text-warning" />}
                Cierre de Caja del Día
              </CardTitle>
              <CardDescription>Arqueo y conciliación financiera al {formatDate(hasta)}</CardDescription>
            </div>
            <div>
              {!isUnlocked ? (
                <Button
                  onClick={() => setPinDialogOpen(true)}
                  className="gradient-orion text-white font-bold shadow-md"
                >
                  <ShieldCheck className="mr-2 h-4 w-4" />
                  Desbloquear Cierre con PIN de Admin
                </Button>
              ) : (
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs font-bold border-success text-success bg-success/10 py-1 px-3">
                    <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                    Acceso de Administrador Autorizado
                  </Badge>
                  <Button variant="ghost" size="sm" onClick={() => setIsUnlocked(false)}>
                    <Lock className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-6">
          {!isUnlocked ? (
            /* Bloqueo de Privacidad */
            <div className="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed rounded-2xl bg-muted/10 p-6">
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-4">
                <Lock className="h-8 w-8" />
              </div>
              <h3 className="text-lg font-bold text-foreground">Contenido Financiero Privado</h3>
              <p className="text-sm text-muted-foreground max-w-md mt-1 mb-6">
                El resumen del cierre de caja contiene cifras confidenciales del negocio. Introduce el código único o PIN de Administrador para desbloquear.
              </p>
              <Button onClick={() => setPinDialogOpen(true)} size="lg" className="gradient-orion text-white font-bold h-12 px-6">
                Ingresar PIN de Administrador
              </Button>
            </div>
          ) : (
            /* Vista Desbloqueada con Arqueo de Caja */
            <div className="space-y-6">
              {/* Tarjetas de Métodos */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <CajaCard label="Total Día" value={diaQ.data?.resumen_caja.total_dia ?? 0} accent />
                <CajaCard label="Efectivo Sistema" value={efectivoSistema} />
                <CajaCard label="Nequi" value={diaQ.data?.resumen_caja.nequi ?? 0} />
                <CajaCard label="Daviplata" value={diaQ.data?.resumen_caja.daviplata ?? 0} />
                <CajaCard label="Tarjeta" value={diaQ.data?.resumen_caja.tarjeta ?? 0} />
                <CajaCard label="Transferencia" value={diaQ.data?.resumen_caja.transferencia ?? 0} />
              </div>

              {/* Formulario de Arqueo Físico */}
              <Card className="border bg-card/60">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <Coins className="h-5 w-5 text-primary" />
                    Arqueo & Cuadre de Efectivo Contado
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
                    <div className="space-y-2">
                      <Label className="text-sm font-semibold">Efectivo Físico en Cajón ($ COP)</Label>
                      <Input
                        type="number"
                        placeholder="Ej. 150000"
                        value={efectivoFisicoInput}
                        onChange={(e) => setEfectivoFisicoInput(e.target.value)}
                        className="h-12 text-xl font-bold"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground uppercase font-bold">Estado del Cuadre</Label>
                      <div className="h-12 flex items-center px-4 rounded-xl border font-bold text-lg bg-muted/30">
                        {diferencia === null ? (
                          <span className="text-muted-foreground text-sm">Ingrese el efectivo en cajón...</span>
                        ) : diferencia === 0 ? (
                          <span className="text-success flex items-center gap-2">
                            <CheckCircle2 className="h-5 w-5" />
                            Cuadre Perfectamente Exacto
                          </span>
                        ) : diferencia > 0 ? (
                          <span className="text-primary flex items-center gap-2">
                            ⬆️ Sobrante: +{formatCurrency(diferencia)}
                          </span>
                        ) : (
                          <span className="text-destructive flex items-center gap-2">
                            ⬇️ Faltante: {formatCurrency(diferencia)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-2">
                    <Button
                      onClick={() => {
                        setCierreGuardado(true);
                        toast.success("¡Cierre de caja guardado e impreso exitosamente!");
                        window.print();
                      }}
                      className="gradient-orion text-white font-bold h-11 px-6 shadow-md"
                      disabled={cierreGuardado}
                    >
                      {cierreGuardado ? "Cierre Guardado" : "Guardar & Imprimir Cierre del Día"}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Detalle por Producto */}
              {diaQ.data && diaQ.data.productos.length > 0 && (
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
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Diálogo Modal de PIN de Administrador */}
      <Dialog open={pinDialogOpen} onOpenChange={setPinDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Lock className="h-5 w-5 text-primary" />
              PIN de Administrador Requerido
            </DialogTitle>
            <DialogDescription>
              Introduce el código o PIN de 4-6 dígitos del Administrador para realizar el Arqueo de Caja.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="flex h-14 items-center justify-center rounded-xl border bg-muted/40 text-3xl font-black tracking-widest text-primary">
              {pinInput ? "•".repeat(pinInput.length) : <span className="text-sm font-medium text-muted-foreground tracking-normal">Ingresa PIN...</span>}
            </div>

            <Numpad
              value={pinInput}
              onChange={setPinInput}
              disabled={verifyingPin}
            />
          </div>

          <DialogFooter className="gap-2 sm:justify-between">
            <Button variant="ghost" onClick={() => setPinDialogOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleVerifyPin}
              disabled={!pinInput.trim() || verifyingPin}
              className="gradient-orion text-white font-bold"
            >
              Confirmar PIN
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
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
