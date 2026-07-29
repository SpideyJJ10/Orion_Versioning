"use client";

import { useState } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  UserCircle2,
  ShieldCheck,
  Key,
} from "lucide-react";
import {
  useUsuarios,
  useSucursales,
  useCrearUsuario,
  useActualizarUsuario,
  useEliminarUsuario,
} from "@/lib/hooks/use-api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { UsuarioFormDialog } from "@/components/usuarios/usuario-form-dialog";
import { useAuthStore } from "@/lib/stores/auth-store";
import { formatDateTime } from "@/lib/formatters";
import type { UsuarioPublico, Sucursal } from "@/lib/api/types";

const ROL_BADGE: Record<string, { label: string; cls: string }> = {
  owner:      { label: "Owner",      cls: "bg-purple-500/15 text-purple-600 border-purple-300/30" },
  manager:    { label: "Manager",    cls: "bg-blue-500/15 text-blue-600 border-blue-300/30" },
  cajero:     { label: "Cajero",     cls: "bg-green-500/15 text-green-600 border-green-300/30" },
  inventario: { label: "Inventario", cls: "bg-orange-500/15 text-orange-600 border-orange-300/30" },
  super_admin:{ label: "Admin",      cls: "bg-red-500/15 text-red-600 border-red-300/30" },
};

export default function UsuariosPage() {
  const user       = useAuthStore((s) => s.user);
  const canMutate  = user ? ["owner", "super_admin"].includes(user.rol) : false;
  const canManage  = user ? ["owner", "manager", "super_admin"].includes(user.rol) : false;

  const usuariosQ  = useUsuarios();
  const sucursalesQ = useSucursales();
  const crearM     = useCrearUsuario();
  const actualizarM = useActualizarUsuario();
  const eliminarM  = useEliminarUsuario();

  const [creating, setCreating] = useState(false);
  const [editing,  setEditing]  = useState<UsuarioPublico & { pin?: string | null } | null>(null);

  const usuarios   = usuariosQ.data ?? [];
  const sucursales = sucursalesQ.data ?? [];

  // Build lookup for sucursal names
  const sucursalNombre = (id: string | null) =>
    id ? (sucursales.find((s: Sucursal) => s.id === id)?.nombre ?? id) : "—";

  async function handleDelete(u: UsuarioPublico) {
    if (!confirm(`¿Desactivar a "${u.nombre}"? Podrás reactivarlo luego.`)) return;
    try {
      await eliminarM.mutateAsync(u.id);
    } catch {
      /* toast en hook */
    }
  }

  if (!canManage) {
    return (
      <div className="flex h-full items-center justify-center p-12">
        <Card>
          <CardContent className="space-y-2 p-10 text-center">
            <ShieldCheck className="mx-auto h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm font-medium">Acceso restringido</p>
            <p className="text-xs text-muted-foreground">
              Solo el owner y manager pueden ver el equipo.
            </p>
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
          <h1 className="text-2xl font-bold">Equipo</h1>
          <p className="text-sm text-muted-foreground">
            Usuarios operativos · {usuarios.length}{" "}
            {usuarios.length === 1 ? "persona" : "personas"}
          </p>
        </div>
        {canMutate && (
          <Button onClick={() => setCreating(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Nuevo usuario
          </Button>
        )}
      </header>

      {/* Table */}
      {usuariosQ.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : usuarios.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 p-12 text-center">
            <UserCircle2 className="h-12 w-12 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              Aún no has creado usuarios para tu equipo.
            </p>
            {canMutate && (
              <Button variant="outline" onClick={() => setCreating(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Crear primer usuario
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
                    <th className="px-4 py-3">Usuario</th>
                    <th className="px-4 py-3">Rol</th>
                    <th className="px-4 py-3">Sucursal</th>
                    <th className="px-4 py-3">PIN</th>
                    {canMutate && <th className="px-4 py-3 text-right">Acciones</th>}
                  </tr>
                </thead>
                <tbody>
                  {usuarios.map((u) => {
                    const badge = ROL_BADGE[u.rol] ?? { label: u.rol, cls: "bg-muted text-muted-foreground" };
                    const isSelf = u.id === user?.id;
                    return (
                      <tr
                        key={u.id}
                        className="border-t transition-colors hover:bg-muted/30"
                      >
                        {/* Avatar + nombre */}
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
                              {(u.nombre || "U").charAt(0).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                              <p className="truncate font-medium">{u.nombre}</p>
                              <p className="truncate text-xs text-muted-foreground">{u.email}</p>
                            </div>
                          </div>
                        </td>
                        {/* Rol */}
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${badge.cls}`}>
                            {badge.label}
                          </span>
                        </td>
                        {/* Sucursal */}
                        <td className="px-4 py-3 text-muted-foreground">
                          {sucursalNombre(u.sucursal_id)}
                        </td>
                        {/* PIN */}
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Key className="h-3 w-3" />
                            ••••
                          </div>
                        </td>
                        {/* Acciones */}
                        {canMutate && (
                          <td className="px-4 py-3">
                            <div className="flex justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setEditing(u as UsuarioPublico & { pin?: string | null })}
                                disabled={isSelf}
                                title="Editar"
                              >
                                <Pencil className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDelete(u)}
                                disabled={isSelf || eliminarM.isPending}
                                title="Desactivar"
                                className="text-muted-foreground hover:text-destructive"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Dialogs */}
      <UsuarioFormDialog
        open={creating}
        onOpenChange={setCreating}
        sucursales={sucursales}
        onSubmit={async (data) => {
          // For creation, password is always set (validated in the form)
          await crearM.mutateAsync(data as import("@/lib/api/types").CrearUsuarioRequest);
          setCreating(false);
        }}
        isPending={crearM.isPending}
      />
      <UsuarioFormDialog
        open={!!editing}
        onOpenChange={(open) => !open && setEditing(null)}
        usuario={editing ?? undefined}
        sucursales={sucursales}
        onSubmit={async (data) => {
          if (!editing) return;
          await actualizarM.mutateAsync({ id: editing.id, data });
          setEditing(null);
        }}
        isPending={actualizarM.isPending}
      />
    </div>
  );
}
