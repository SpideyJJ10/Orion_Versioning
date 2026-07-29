"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { UsuarioPublico, Sucursal, CrearUsuarioRequest } from "@/lib/api/types";

interface UsuarioFormDialogProps {
  open:         boolean;
  onOpenChange: (open: boolean) => void;
  usuario?:     UsuarioPublico & { pin?: string | null };
  sucursales:   Sucursal[];
  onSubmit:     (data: Omit<CrearUsuarioRequest, "password"> & { password?: string }) => Promise<void>;
  isPending:    boolean;
}

const ROL_OPTIONS = [
  { value: "cajero",     label: "Cajero" },
  { value: "manager",   label: "Manager" },
  { value: "inventario", label: "Inventario" },
];

export function UsuarioFormDialog({
  open,
  onOpenChange,
  usuario,
  sucursales,
  onSubmit,
  isPending,
}: UsuarioFormDialogProps) {
  const isEditing = !!usuario;

  const [nombre,      setNombre]      = useState("");
  const [email,       setEmail]       = useState("");
  const [password,    setPassword]    = useState("");
  const [rol,         setRol]         = useState<string>("cajero");
  const [sucursalId,  setSucursalId]  = useState<string>("none");
  const [pin,         setPin]         = useState<string>("");
  const [errors,      setErrors]      = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      if (usuario) {
        setNombre(usuario.nombre);
        setEmail(usuario.email);
        setRol(usuario.rol);
        setSucursalId(usuario.sucursal_id ?? "none");
        setPin("");
        setPassword("");
      } else {
        setNombre("");
        setEmail("");
        setPassword("");
        setRol("cajero");
        setSucursalId("none");
        setPin("");
      }
      setErrors({});
    }
  }, [open, usuario, sucursales]);

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (!nombre.trim()) e.nombre = "Nombre requerido";
    if (!isEditing && !email.trim()) e.email = "Email requerido";
    if (!isEditing && password.length < 6) e.password = "Mínimo 6 caracteres";
    if (pin && !/^[0-9]{4,6}$/.test(pin)) e.pin = "PIN debe ser 4-6 dígitos numéricos";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    try {
      await onSubmit({
        nombre,
        email: email.trim().toLowerCase(),
        ...(password ? { password } : {}),
        rol: rol as CrearUsuarioRequest["rol"],
        sucursal_id: sucursalId && sucursalId !== "none" ? sucursalId : null,
        pin: pin || null,
      });
    } catch {
      /* handled by hook */
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? "Editar usuario" : "Nuevo usuario"}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? `Editando a ${usuario?.nombre}`
              : "Crea un acceso para un miembro de tu equipo."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Nombre */}
          <div className="space-y-1">
            <Label htmlFor="u-nombre">Nombre completo *</Label>
            <Input
              id="u-nombre"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Juan García"
              disabled={isPending}
            />
            {errors.nombre && <p className="text-xs text-destructive">{errors.nombre}</p>}
          </div>

          {/* Email (solo creación) */}
          {!isEditing && (
            <div className="space-y-1">
              <Label htmlFor="u-email">Email *</Label>
              <Input
                id="u-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="juan@miempresa.com"
                disabled={isPending}
              />
              {errors.email && <p className="text-xs text-destructive">{errors.email}</p>}
            </div>
          )}

          {/* Password */}
          <div className="space-y-1">
            <Label htmlFor="u-password">
              Contraseña {isEditing ? "(dejar vacío para no cambiar)" : "*"}
            </Label>
            <Input
              id="u-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isEditing ? "••••••" : "Mínimo 6 caracteres"}
              disabled={isPending}
            />
            {errors.password && <p className="text-xs text-destructive">{errors.password}</p>}
          </div>

          {/* Rol */}
          <div className="space-y-1">
            <Label>Rol *</Label>
            <Select value={rol} onValueChange={setRol} disabled={isPending}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROL_OPTIONS.map((r) => (
                  <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Sucursal */}
          <div className="space-y-1">
            <Label>Sucursal asignada</Label>
            <Select value={sucursalId} onValueChange={setSucursalId} disabled={isPending}>
              <SelectTrigger>
                <SelectValue placeholder="Sin asignar" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Sin asignar (todas)</SelectItem>
                {sucursales.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* PIN */}
          <div className="space-y-1">
            <Label htmlFor="u-pin">
              PIN rápido{" "}
              <span className="text-xs text-muted-foreground">(4–6 dígitos, opcional)</span>
            </Label>
            <Input
              id="u-pin"
              type="password"
              inputMode="numeric"
              maxLength={6}
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="1234"
              disabled={isPending}
            />
            {errors.pin && <p className="text-xs text-destructive">{errors.pin}</p>}
            <p className="text-xs text-muted-foreground">
              El PIN permite al cajero acceder sin email ni contraseña.
            </p>
          </div>

          <DialogFooter className="gap-2 pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEditing ? "Guardar cambios" : "Crear usuario"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
