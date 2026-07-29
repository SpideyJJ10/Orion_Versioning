"use client";

import { useState } from "react";
import { useMesas, useSucursales, useActualizarMesaEstado } from "@/lib/hooks/use-api";
import { useAuthStore } from "@/lib/stores/auth-store";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Users, Info, Settings2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import type { MesaOut } from "@/lib/api/mesas";

export default function MesasPage() {
  const { data: sucursales } = useSucursales();
  const [sucursalId, setSucursalId] = useState<string | undefined>();
  const effectiveSucursalId = sucursalId ?? sucursales?.[0]?.id;

  const mesasQ = useMesas(effectiveSucursalId);
  const actualizarEstadoM = useActualizarMesaEstado();

  const mesas = mesasQ.data ?? [];

  async function handleToggleMesa(mesa: MesaOut) {
    const nuevoEstado = mesa.estado === "libre" ? "ocupada" : "libre";
    try {
      await actualizarEstadoM.mutateAsync({
        id: mesa.id,
        estado: nuevoEstado,
      });
      toast.success(`Mesa ${mesa.numero} ahora está ${nuevoEstado}`);
    } catch (e) {
      // toast in hook
    }
  }

  if (!effectiveSucursalId) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            No hay sucursales disponibles.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Plano de Mesas</h1>
          <p className="text-sm text-muted-foreground">
            Visualiza y administra las mesas de tu restaurante.
          </p>
        </div>
        <div className="flex gap-2">
          {sucursales && sucursales.length > 1 && (
            <Select value={effectiveSucursalId} onValueChange={setSucursalId}>
              <SelectTrigger className="w-44">
                <SelectValue />
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
        </div>
      </header>

      {mesasQ.isLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square w-full rounded-xl" />
          ))}
        </div>
      ) : mesas.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Info className="mb-2 h-10 w-10 text-muted-foreground" />
            <p className="text-lg font-semibold">No hay mesas configuradas</p>
            <p className="text-sm text-muted-foreground text-center">
              Aún no tienes mesas en esta sucursal.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {mesas.map((mesa) => {
            const isOcupada = mesa.estado !== "libre";
            return (
              <button
                key={mesa.id}
                onClick={() => handleToggleMesa(mesa)}
                disabled={actualizarEstadoM.isPending}
                className={`relative flex aspect-square flex-col items-center justify-center gap-2 rounded-xl border p-4 text-center transition-all hover:scale-[1.02] active:scale-95 ${
                  isOcupada
                    ? "border-primary bg-primary/10 text-primary shadow-sm"
                    : "border-border bg-card text-foreground hover:border-primary/50"
                }`}
              >
                <span className="text-3xl font-black">
                  {mesa.numero}
                </span>
                {mesa.nombre && (
                  <span className="text-xs font-medium uppercase tracking-wider opacity-70">
                    {mesa.nombre}
                  </span>
                )}
                <div className="mt-2 flex items-center gap-1 text-[10px] font-semibold opacity-60">
                  <Users className="h-3 w-3" />
                  {mesa.capacidad}
                </div>
                
                {isOcupada && (
                  <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-primary animate-pulse" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
