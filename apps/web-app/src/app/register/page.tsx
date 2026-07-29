"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/auth-store";
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
import { Card, CardContent } from "@/components/ui/card";
import { OrionLogo } from "@/components/brand/orion-logo";
import type { RegisterRequest } from "@/lib/api/types";

const NICHOS: { value: RegisterRequest["nicho"]; label: string }[] = [
  { value: "restaurante", label: "Restaurante / Cafetería" },
  { value: "retail",      label: "Tienda / Retail" },
  { value: "farmacia",    label: "Farmacia / Droguería" },
  { value: "servicio",    label: "Servicios" },
  { value: "otro",        label: "Otro" },
];

export default function RegisterPage() {
  const router     = useRouter();
  const setSession = useAuthStore((s) => s.setSession);

  const [form, setForm] = useState<RegisterRequest>({
    email:              "",
    password:           "",
    nombre_comercial:   "",
    nombre_propietario: "",
    telefono:           "",
    nicho:              "restaurante",
  });
  const [loading, setLoading] = useState(false);

  function update<K extends keyof RegisterRequest>(key: K, value: RegisterRequest[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password.length < 8) {
      toast.error("La contraseña debe tener al menos 8 caracteres");
      return;
    }
    setLoading(true);
    try {
      const tokens = await authApi.register({
        ...form,
        email: form.email.trim().toLowerCase(),
      });
      setSession(tokens.access_token, tokens.refresh_token, tokens.usuario);
      toast.success("¡Negocio creado! Bienvenido a Orion");
      router.replace("/dashboard");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al crear la cuenta");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 p-6">
      {/* Logo */}
      <div className="mb-8 flex flex-col items-center gap-3">
        <OrionLogo variant="mark" size="lg" />
        <OrionLogo variant="wordmark" size="md" />
        <p className="text-sm text-muted-foreground">
          Crea tu negocio en menos de 2 minutos
        </p>
      </div>

      <Card className="w-full max-w-lg">
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="nombre_comercial">Nombre del negocio *</Label>
                <Input
                  id="nombre_comercial"
                  required
                  placeholder="Mi Restaurante"
                  value={form.nombre_comercial}
                  onChange={(e) => update("nombre_comercial", e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="nombre_propietario">Tu nombre *</Label>
                <Input
                  id="nombre_propietario"
                  required
                  placeholder="Juan García"
                  value={form.nombre_propietario}
                  onChange={(e) => update("nombre_propietario", e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="reg-email">Correo electrónico *</Label>
                <Input
                  id="reg-email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="tu@negocio.com"
                  value={form.email}
                  onChange={(e) => update("email", e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="telefono">Teléfono</Label>
                <Input
                  id="telefono"
                  type="tel"
                  placeholder="300 123 4567"
                  value={form.telefono ?? ""}
                  onChange={(e) => update("telefono", e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="reg-password">Contraseña *</Label>
                <Input
                  id="reg-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  placeholder="Mínimo 8 caracteres"
                  value={form.password}
                  onChange={(e) => update("password", e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="nicho">Tipo de negocio *</Label>
                <Select
                  value={form.nicho}
                  onValueChange={(v) => update("nicho", v as RegisterRequest["nicho"])}
                >
                  <SelectTrigger id="nicho" disabled={loading}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {NICHOS.map((n) => (
                      <SelectItem key={n.value} value={n.value}>{n.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button type="submit" className="w-full" size="lg" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Crear mi negocio
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              ¿Ya tienes cuenta?{" "}
              <Link className="font-medium text-primary hover:underline" href="/login">
                Iniciar sesión
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>

      <p className="mt-8 text-xs text-muted-foreground">
        © 2025 Orion Tech · Todos los derechos reservados
      </p>
    </div>
  );
}
