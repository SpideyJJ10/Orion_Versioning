"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Loader2, Trash2, Edit, Save, X, Settings } from "lucide-react";

import { adminApi } from "@/lib/api";
import type { TenantAdmin } from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useRouter } from "next/navigation";

export default function AdminPage() {
  const [tenants, setTenants] = useState<TenantAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Edit State
  const [editingTenant, setEditingTenant] = useState<TenantAdmin | null>(null);
  const [editLoading, setEditLoading] = useState(false);
  const [editData, setEditData] = useState<Partial<TenantAdmin>>({});

  // Delete State
  const [deletingTenant, setDeletingTenant] = useState<TenantAdmin | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const { hasRole } = useAuthStore();
  const isSuperAdmin = hasRole('super_admin');
  const router = useRouter();

  useEffect(() => {
    if (isSuperAdmin === false) {
      router.replace("/dashboard");
      return;
    }
    if (isSuperAdmin) {
      loadTenants();
    }
  }, [isSuperAdmin, router]);

  async function loadTenants() {
    try {
      const data = await adminApi.getTenants();
      setTenants(data);
    } catch (error) {
      toast.error("Error al cargar negocios");
    } finally {
      setLoading(false);
    }
  }

  function handleEditClick(tenant: TenantAdmin) {
    setEditingTenant(tenant);
    setEditData({
      nombre: tenant.nombre,
      email: tenant.email,
      plan: tenant.plan,
      plan_activo: tenant.plan_activo,
      fecha_vencimiento: tenant.fecha_vencimiento,
    });
  }

  async function handleSaveEdit() {
    if (!editingTenant) return;
    setEditLoading(true);
    try {
      const data = await adminApi.updateTenant(editingTenant.id, editData as any);
      setTenants((prev) => prev.map((t) => (t.id === data.id ? data : t)));
      toast.success("Negocio actualizado exitosamente");
      setEditingTenant(null);
    } catch (error) {
      toast.error("Error al actualizar negocio");
    } finally {
      setEditLoading(false);
    }
  }

  async function handleDeleteConfirm() {
    if (!deletingTenant) return;
    setDeleteLoading(true);
    try {
      await adminApi.deleteTenant(deletingTenant.id);
      setTenants((prev) => prev.filter((t) => t.id !== deletingTenant.id));
      toast.success("Negocio eliminado");
      setDeletingTenant(null);
    } catch (error) {
      toast.error("Error al eliminar negocio");
    } finally {
      setDeleteLoading(false);
    }
  }

  if (loading || isSuperAdmin === null) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!isSuperAdmin) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Panel de Fundador</h1>
          <p className="text-muted-foreground">
            Administra todos los negocios (tenants) registrados en la plataforma.
          </p>
        </div>
      </div>

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Nombre</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Creado el</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tenants.map((tenant) => (
              <TableRow key={tenant.id}>
                <TableCell className="font-mono text-xs">{tenant.id}</TableCell>
                <TableCell className="font-medium">{tenant.nombre || "Sin nombre"}</TableCell>
                <TableCell>{tenant.email}</TableCell>
                <TableCell className="capitalize">{tenant.plan}</TableCell>
                <TableCell>
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      tenant.plan_activo
                        ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                    }`}
                  >
                    {tenant.plan_activo ? "Activo" : "Inactivo"}
                  </span>
                </TableCell>
                <TableCell>
                  {tenant.creado_en
                    ? format(new Date(tenant.creado_en), "dd MMM yyyy", { locale: es })
                    : "—"}
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleEditClick(tenant)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive hover:bg-destructive/10"
                    onClick={() => setDeletingTenant(tenant)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {tenants.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-6">
                  No hay negocios registrados.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Edit Dialog */}
      <Dialog open={!!editingTenant} onOpenChange={(o) => !o && setEditingTenant(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Negocio</DialogTitle>
            <DialogDescription>
              Modifica la información y estado del negocio.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Nombre Comercial</Label>
              <Input
                value={editData.nombre || ""}
                onChange={(e) => setEditData({ ...editData, nombre: e.target.value })}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Email (Acceso)</Label>
              <Input
                type="email"
                value={editData.email || ""}
                onChange={(e) => setEditData({ ...editData, email: e.target.value })}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Plan</Label>
              <Input
                value={editData.plan || ""}
                onChange={(e) => setEditData({ ...editData, plan: e.target.value })}
              />
            </div>

            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="space-y-0.5">
                <Label>Estado del Plan</Label>
                <div className="text-[13px] text-muted-foreground">
                  Activar o suspender cuenta
                </div>
              </div>
              <Switch
                checked={editData.plan_activo}
                onCheckedChange={(c) => setEditData({ ...editData, plan_activo: c })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingTenant(null)} disabled={editLoading}>
              Cancelar
            </Button>
            <Button onClick={handleSaveEdit} disabled={editLoading}>
              {editLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Guardar Cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deletingTenant} onOpenChange={(o) => !o && setDeletingTenant(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar este negocio?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. Se eliminarán permanentemente todos
              los datos, ventas, y usuarios del negocio <b>{deletingTenant?.nombre}</b>.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteLoading}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive hover:bg-destructive/90"
              onClick={handleDeleteConfirm}
              disabled={deleteLoading}
            >
              {deleteLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Sí, Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
