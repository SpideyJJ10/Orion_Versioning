"use client";

import { useState } from "react";
import {
  useMesas,
  useSucursales,
  useActualizarMesaEstado,
  useCrearMesa,
  useCrearMesasBulk,
} from "@/lib/hooks/use-api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Users,
  Info,
  Plus,
  ShoppingCart,
  CheckCircle2,
  Clock,
  CalendarDays,
  Settings2,
  Trash2,
  UtensilsCrossed,
  ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { useRouter } from "next/navigation";
import type { MesaOut } from "@/lib/api/mesas";
import { api } from "@/lib/api";

type EstadoFilter = "todas" | "libre" | "ocupada" | "cuenta_pedida" | "reservada";

const STATUS_CONFIG: Record<string, { label: string; badgeClass: string; cardClass: string; icon: any }> = {
  libre: {
    label: "Disponible",
    badgeClass: "border-success text-success bg-success/10",
    cardClass: "border-border bg-card hover:border-success/50",
    icon: CheckCircle2,
  },
  ocupada: {
    label: "Ocupada",
    badgeClass: "border-destructive text-destructive bg-destructive/10",
    cardClass: "border-destructive/50 bg-destructive/5 text-foreground shadow-sm",
    icon: UtensilsCrossed,
  },
  cuenta_pedida: {
    label: "Cuenta Pedida",
    badgeClass: "border-warning text-warning-foreground bg-warning/20",
    cardClass: "border-warning/50 bg-warning/10 text-foreground shadow-sm",
    icon: Clock,
  },
  reservada: {
    label: "Reservada",
    badgeClass: "border-primary text-primary bg-primary/10",
    cardClass: "border-primary/50 bg-primary/5 text-foreground",
    icon: CalendarDays,
  },
};

export default function MesasPage() {
  const router = useRouter();
  const { data: sucursales } = useSucursales();
  const [sucursalId, setSucursalId] = useState<string | undefined>();
  const effectiveSucursalId = sucursalId ?? sucursales?.[0]?.id;

  const mesasQ = useMesas(effectiveSucursalId);
  const actualizarEstadoM = useActualizarMesaEstado();
  const crearMesaM = useCrearMesa();
  const crearMesasBulkM = useCrearMesasBulk();

  const [filter, setFilter] = useState<EstadoFilter>("todas");
  const [selectedMesa, setSelectedMesa] = useState<MesaOut | null>(null);
  const [addModalOpen, setAddModalOpen] = useState(false);

  // Formulario de nueva mesa
  const [newNumero, setNewNumero] = useState<number>(1);
  const [newNombre, setNewNombre] = useState<string>("");
  const [newCapacidad, setNewCapacidad] = useState<number>(4);
  const [isBulk, setIsBulk] = useState(false);
  const [bulkCantidad, setBulkCantidad] = useState<number>(5);

  // Formulario de edición de mesa
  const [editNombre, setEditNombre] = useState<string>("");
  const [editCapacidad, setEditCapacidad] = useState<number>(4);

  const mesas = mesasQ.data ?? [];

  const filteredMesas = mesas.filter((m) => {
    if (filter === "todas") return true;
    return m.estado === filter;
  });

  const countLibres = mesas.filter((m) => m.estado === "libre").length;
  const countOcupadas = mesas.filter((m) => m.estado === "ocupada").length;
  const countCuenta = mesas.filter((m) => m.estado === "cuenta_pedida").length;
  const countReservadas = mesas.filter((m) => m.estado === "reservada").length;

  const handleOpenMesaModal = (mesa: MesaOut) => {
    setSelectedMesa(mesa);
    setEditNombre(mesa.nombre ?? "");
    setEditCapacidad(mesa.capacidad ?? 4);
  };

  const handleChangeEstado = async (nuevoEstado: string) => {
    if (!selectedMesa) return;
    try {
      await actualizarEstadoM.mutateAsync({
        id: selectedMesa.id,
        estado: nuevoEstado as any,
      });
      toast.success(`Mesa ${selectedMesa.numero} cambió a ${STATUS_CONFIG[nuevoEstado]?.label}`);
      setSelectedMesa((prev) => (prev ? { ...prev, estado: nuevoEstado } : null));
    } catch {
      // handled by hook
    }
  };

  const handleUpdateMesaProps = async () => {
    if (!selectedMesa) return;
    try {
      await api.patch(`/api/mesas/${selectedMesa.id}`, {
        nombre: editNombre || null,
        capacidad: editCapacidad,
      });
      toast.success("Características de la mesa actualizadas");
      mesasQ.refetch();
      setSelectedMesa(null);
    } catch {
      toast.error("Error al actualizar la mesa");
    }
  };

  const handleCreateMesaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveSucursalId) return;

    try {
      if (isBulk) {
        await crearMesasBulkM.mutateAsync({
          sucursal_id: effectiveSucursalId,
          cantidad: bulkCantidad,
          capacidad: newCapacidad,
        });
        toast.success(`¡${bulkCantidad} mesas creadas exitosamente!`);
      } else {
        await crearMesaM.mutateAsync({
          sucursal_id: effectiveSucursalId,
          numero: newNumero,
          nombre: newNombre || undefined,
          capacidad: newCapacidad,
        });
        toast.success(`¡Mesa ${newNumero} creada exitosamente!`);
      }
      setAddModalOpen(false);
      setNewNombre("");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Error al crear la mesa");
    }
  };

  return (
    <div className="space-y-6 p-6 md:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b pb-5">
        <div>
          <h1 className="text-3xl font-black tracking-tight">Plano & Gestión de Mesas</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Visualización interactiva en tiempo real y asignación de órdenes para tu salón.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {sucursales && sucursales.length > 1 && (
            <Select value={effectiveSucursalId} onValueChange={setSucursalId}>
              <SelectTrigger className="w-48 h-11">
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

          <Button
            onClick={() => {
              const nextNum = mesas.length > 0 ? Math.max(...mesas.map((m) => m.numero)) + 1 : 1;
              setNewNumero(nextNum);
              setAddModalOpen(true);
            }}
            className="gradient-orion text-white font-bold h-11 px-5 shadow-md"
          >
            <Plus className="mr-2 h-4 w-4" />
            Nueva Mesa
          </Button>
        </div>
      </header>

      {/* Badges de Estado Rápido */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="p-4 flex items-center justify-between border-l-4 border-l-success">
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase">Disponibles</p>
            <p className="text-2xl font-black text-foreground mt-0.5">{countLibres}</p>
          </div>
          <CheckCircle2 className="h-6 w-6 text-success" />
        </Card>

        <Card className="p-4 flex items-center justify-between border-l-4 border-l-destructive">
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase">Ocupadas</p>
            <p className="text-2xl font-black text-foreground mt-0.5">{countOcupadas}</p>
          </div>
          <UtensilsCrossed className="h-6 w-6 text-destructive" />
        </Card>

        <Card className="p-4 flex items-center justify-between border-l-4 border-l-warning">
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase">Cuenta Pedida</p>
            <p className="text-2xl font-black text-foreground mt-0.5">{countCuenta}</p>
          </div>
          <Clock className="h-6 w-6 text-warning" />
        </Card>

        <Card className="p-4 flex items-center justify-between border-l-4 border-l-primary">
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase">Reservadas</p>
            <p className="text-2xl font-black text-foreground mt-0.5">{countReservadas}</p>
          </div>
          <CalendarDays className="h-6 w-6 text-primary" />
        </Card>
      </div>

      {/* Filtros de Pestaña */}
      <Tabs defaultValue="todas" onValueChange={(val) => setFilter(val as EstadoFilter)}>
        <TabsList className="h-11">
          <TabsTrigger value="todas" className="font-bold">
            Todas ({mesas.length})
          </TabsTrigger>
          <TabsTrigger value="libre" className="font-bold">
            Disponibles ({countLibres})
          </TabsTrigger>
          <TabsTrigger value="ocupada" className="font-bold">
            Ocupadas ({countOcupadas})
          </TabsTrigger>
          <TabsTrigger value="cuenta_pedida" className="font-bold">
            Cuenta Pedida ({countCuenta})
          </TabsTrigger>
          <TabsTrigger value="reservada" className="font-bold">
            Reservadas ({countReservadas})
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Grid de Mesas */}
      {mesasQ.isLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square w-full rounded-2xl" />
          ))}
        </div>
      ) : filteredMesas.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Info className="mb-3 h-12 w-12 text-muted-foreground/30" />
            <h3 className="text-lg font-bold">No se encontraron mesas</h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-1 mb-4">
              {filter === "todas"
                ? "Aún no has agregado mesas para esta sucursal."
                : `No hay mesas en estado '${filter}' en este momento.`}
            </p>
            <Button onClick={() => setAddModalOpen(true)} className="gradient-orion text-white font-bold">
              + Agregar Primera Mesa
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {filteredMesas.map((mesa) => {
            const config = STATUS_CONFIG[mesa.estado] ?? STATUS_CONFIG.libre;
            const IconComp = config.icon;
            const isOcupada = mesa.estado === "ocupada";

            return (
              <button
                key={mesa.id}
                type="button"
                onClick={() => handleOpenMesaModal(mesa)}
                className={`relative flex aspect-square flex-col items-center justify-between rounded-2xl border p-4 text-center transition-all hover:scale-[1.03] active:scale-95 shadow-sm hover:shadow-md ${config.cardClass}`}
              >
                {/* Header card info */}
                <div className="flex w-full items-center justify-between">
                  <Badge variant="outline" className={`text-[10px] font-bold ${config.badgeClass}`}>
                    {config.label}
                  </Badge>
                  <div className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
                    <Users className="h-3.5 w-3.5" />
                    {mesa.capacidad}
                  </div>
                </div>

                {/* Número gigante */}
                <div className="my-auto flex flex-col items-center">
                  <span className="text-4xl font-black tracking-tight">{mesa.numero}</span>
                  {mesa.nombre && (
                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground mt-0.5">
                      {mesa.nombre}
                    </span>
                  )}
                </div>

                {/* Status indicator pulse */}
                {isOcupada && (
                  <span className="absolute right-3 top-3 h-2.5 w-2.5 rounded-full bg-destructive animate-ping" />
                )}

                <div className="w-full flex items-center justify-center text-[10px] font-bold uppercase tracking-wider opacity-60">
                  <IconComp className="mr-1 h-3 w-3" />
                  Mesa #{mesa.numero}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Modal de Detalle & Control de Mesa */}
      {selectedMesa && (
        <Dialog open={!!selectedMesa} onOpenChange={() => setSelectedMesa(null)}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <div className="flex items-center justify-between">
                <DialogTitle className="text-2xl font-black flex items-center gap-2">
                  Mesa #{selectedMesa.numero}
                  {selectedMesa.nombre && <span className="text-sm font-normal text-muted-foreground">({selectedMesa.nombre})</span>}
                </DialogTitle>
                <Badge className={STATUS_CONFIG[selectedMesa.estado]?.badgeClass}>
                  {STATUS_CONFIG[selectedMesa.estado]?.label}
                </Badge>
              </div>
              <DialogDescription>
                Administra el estado, vinculación con el POS y características de la mesa.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6 py-2">
              {/* Acciones Rápidas de Estado */}
              <div className="space-y-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Cambiar Estado de Mesa
                </Label>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    variant={selectedMesa.estado === "libre" ? "default" : "outline"}
                    onClick={() => handleChangeEstado("libre")}
                    className={selectedMesa.estado === "libre" ? "bg-success text-white font-bold" : ""}
                  >
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Disponible / Libre
                  </Button>

                  <Button
                    variant={selectedMesa.estado === "ocupada" ? "default" : "outline"}
                    onClick={() => handleChangeEstado("ocupada")}
                    className={selectedMesa.estado === "ocupada" ? "bg-destructive text-white font-bold" : ""}
                  >
                    <UtensilsCrossed className="mr-2 h-4 w-4" />
                    Ocupada (Clientes)
                  </Button>

                  <Button
                    variant={selectedMesa.estado === "cuenta_pedida" ? "default" : "outline"}
                    onClick={() => handleChangeEstado("cuenta_pedida")}
                    className={selectedMesa.estado === "cuenta_pedida" ? "bg-warning text-warning-foreground font-bold" : ""}
                  >
                    <Clock className="mr-2 h-4 w-4" />
                    Cuenta Pedida
                  </Button>

                  <Button
                    variant={selectedMesa.estado === "reservada" ? "default" : "outline"}
                    onClick={() => handleChangeEstado("reservada")}
                    className={selectedMesa.estado === "reservada" ? "bg-primary text-white font-bold" : ""}
                  >
                    <CalendarDays className="mr-2 h-4 w-4" />
                    Reservada
                  </Button>
                </div>
              </div>

              {/* Botón para abrir POS */}
              <Button
                onClick={() => {
                  router.push(`/pos?mesa=${selectedMesa.numero}`);
                }}
                className="w-full h-12 text-base font-bold gradient-orion text-white shadow-md"
              >
                <ShoppingCart className="mr-2 h-5 w-5" />
                Abrir Punto de Venta (Mesa #{selectedMesa.numero})
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>

              {/* Edición de Características */}
              <div className="space-y-4 border-t pt-4">
                <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                  <Settings2 className="h-3.5 w-3.5" />
                  Características de la Mesa
                </Label>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label className="text-xs">Ubicación / Nombre Custom</Label>
                    <Input
                      placeholder="Ej. Terraza, VIP, Barra"
                      value={editNombre}
                      onChange={(e) => setEditNombre(e.target.value)}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs">Capacidad (Comensales)</Label>
                    <Select
                      value={editCapacidad.toString()}
                      onValueChange={(val) => setEditCapacidad(Number(val))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[2, 4, 6, 8, 10, 12, 16, 20].map((c) => (
                          <SelectItem key={c} value={c.toString()}>
                            {c} Personas
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </div>

            <DialogFooter className="gap-2 sm:justify-between">
              <Button variant="ghost" onClick={() => setSelectedMesa(null)}>
                Cerrar
              </Button>
              <Button onClick={handleUpdateMesaProps} className="font-bold">
                Guardar Cambios
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Modal de Agregar Mesa */}
      <Dialog open={addModalOpen} onOpenChange={setAddModalOpen}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={handleCreateMesaSubmit}>
            <DialogHeader>
              <DialogTitle className="text-xl font-bold">Agregar Nuevas Mesas</DialogTitle>
              <DialogDescription>Configura mesas individuales o en lote para tu salón.</DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="flex items-center justify-between border p-3 rounded-xl bg-muted/20">
                <Label className="text-sm font-semibold">¿Crear mesas en lote (Bulk)?</Label>
                <input
                  type="checkbox"
                  checked={isBulk}
                  onChange={(e) => setIsBulk(e.target.checked)}
                  className="h-5 w-5 rounded border-primary text-primary focus:ring-primary"
                />
              </div>

              {!isBulk ? (
                <>
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold">Número de Mesa</Label>
                    <Input
                      type="number"
                      min={1}
                      value={newNumero}
                      onChange={(e) => setNewNumero(Number(e.target.value))}
                      required
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold">Ubicación / Nombre (Opcional)</Label>
                    <Input
                      placeholder="Ej. Terraza 1, VIP, Salón Principal"
                      value={newNombre}
                      onChange={(e) => setNewNombre(e.target.value)}
                    />
                  </div>
                </>
              ) : (
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Cantidad de mesas a crear</Label>
                  <Input
                    type="number"
                    min={1}
                    max={50}
                    value={bulkCantidad}
                    onChange={(e) => setBulkCantidad(Number(e.target.value))}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    Se crearán {bulkCantidad} mesas numeradas automáticamente.
                  </p>
                </div>
              )}

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Capacidad por Mesa</Label>
                <Select
                  value={newCapacidad.toString()}
                  onValueChange={(val) => setNewCapacidad(Number(val))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[2, 4, 6, 8, 10, 12].map((c) => (
                      <SelectItem key={c} value={c.toString()}>
                        {c} Comensales
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter className="gap-2 sm:justify-between">
              <Button type="button" variant="ghost" onClick={() => setAddModalOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" className="gradient-orion text-white font-bold">
                {isBulk ? `Crear ${bulkCantidad} Mesas` : "Crear Mesa"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
