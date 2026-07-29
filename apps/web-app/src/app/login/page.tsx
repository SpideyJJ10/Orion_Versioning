"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { OrionLogo } from "@/components/brand/orion-logo";

export default function LoginPage() {
  const router     = useRouter();
  const setSession = useAuthStore((s) => s.setSession);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 p-6">
      {/* Logo centrado */}
      <div className="mb-8 flex flex-col items-center gap-3">
        <OrionLogo variant="mark" size="xl" />
        <OrionLogo variant="wordmark" size="lg" />
        <p className="text-sm text-muted-foreground">
          Punto de venta con inteligencia integrada
        </p>
      </div>

      <Card className="w-full max-w-md">
        <CardContent className="pt-4">
          <Tabs defaultValue="email" className="space-y-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="email">Email</TabsTrigger>
              <TabsTrigger value="pin">PIN rápido</TabsTrigger>
            </TabsList>

            <TabsContent value="email">
              <EmailLoginForm onSuccess={(tokens) => {
                setSession(tokens.access_token, tokens.refresh_token, tokens.usuario);
                toast.success(`¡Bienvenido${tokens.usuario.nombre ? ", " + tokens.usuario.nombre : ""}!`);
                router.replace("/dashboard");
              }} />
            </TabsContent>

            <TabsContent value="pin">
              <PinLoginForm onSuccess={(tokens) => {
                setSession(tokens.access_token, tokens.refresh_token, tokens.usuario);
                toast.success(`¡Bienvenido${tokens.usuario.nombre ? ", " + tokens.usuario.nombre : ""}!`);
                router.replace("/dashboard");
              }} />
            </TabsContent>
          </Tabs>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            ¿Aún no tienes cuenta?{" "}
            <Link className="font-medium text-primary hover:underline" href="/register">
              Crear mi negocio
            </Link>
          </p>
        </CardContent>
      </Card>

      <p className="mt-8 text-xs text-muted-foreground">
        © 2025 Orion Tech · Orion POS
      </p>
    </div>
  );
}

// ─── Email/Password Form ─────────────────────────────────────────────────────
function EmailLoginForm({ onSuccess }: { onSuccess: (tokens: Awaited<ReturnType<typeof authApi.login>>) => void }) {
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const tokens = await authApi.login({ email: email.trim().toLowerCase(), password });
      onSuccess(tokens);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Credenciales incorrectas");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">Correo electrónico</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={loading}
          placeholder="tu@negocio.com"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Contraseña</Label>
        <div className="relative">
          <Input
            id="password"
            type={showPass ? "text" : "password"}
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            className="pr-10"
          />
          <button
            type="button"
            onClick={() => setShowPass(!showPass)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            tabIndex={-1}
          >
            {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>
      <Button type="submit" className="w-full" disabled={loading}>
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Iniciar sesión
      </Button>
    </form>
  );
}

// ─── PIN Form ────────────────────────────────────────────────────────────────
function PinLoginForm({ onSuccess }: { onSuccess: (tokens: Awaited<ReturnType<typeof authApi.login>>) => void }) {
  const [tenantId, setTenantId] = useState<string>("");
  const [pin,      setPin]      = useState<string>("");
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!tenantId || pin.length < 4) {
      toast.error("Ingresa el ID del negocio y el PIN");
      return;
    }
    setLoading(true);
    try {
      const tokens = await authApi.loginPin({
        tenant_id: Number(tenantId),
        pin,
      });
      onSuccess(tokens as Awaited<ReturnType<typeof authApi.login>>);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "PIN incorrecto");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="tenant-id">ID del negocio</Label>
        <Input
          id="tenant-id"
          type="number"
          inputMode="numeric"
          value={tenantId}
          onChange={(e) => setTenantId(e.target.value)}
          placeholder="12345"
          disabled={loading}
          required
        />
        <p className="text-xs text-muted-foreground">
          Solicita el ID de negocio a tu administrador.
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="pin-input">PIN</Label>
        <Input
          id="pin-input"
          type="password"
          inputMode="numeric"
          maxLength={6}
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
          placeholder="••••"
          disabled={loading}
          required
        />
      </div>
      <Button type="submit" className="w-full" disabled={loading}>
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Entrar con PIN
      </Button>
    </form>
  );
}
