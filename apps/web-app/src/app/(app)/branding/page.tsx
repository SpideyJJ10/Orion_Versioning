"use client";

import { useEffect, useState } from "react";
import { Palette, Save, Loader2, Eye } from "lucide-react";
import { useBrandingQuery, useUpdateBranding } from "@/lib/hooks/use-api";
import { useBrandingStore } from "@/lib/stores/branding-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuthStore } from "@/lib/stores/auth-store";
import type { Branding, BrandingUpdateRequest, BrandingTema } from "@/lib/api/types";

const NICHOS = [
  { value: "restaurante", label: "Restaurante / Comida" },
  { value: "retail",      label: "Retail / Tienda" },
  { value: "farmacia",    label: "Farmacia" },
  { value: "servicio",    label: "Servicio" },
  { value: "otro",        label: "Otro" },
];

const TEMAS: { value: BrandingTema; label: string }[] = [
  { value: "dark",  label: "Oscuro" },
  { value: "light", label: "Claro" },
  { value: "warm",  label: "Cálido" },
];

const TIPOGRAFIAS = ["Inter", "Roboto", "Poppins", "Outfit", "Nunito", "DM Sans"];

export default function BrandingPage() {
  const user     = useAuthStore((s) => s.user);
  const canEdit  = user ? ["owner", "super_admin"].includes(user.rol) : false;

  const brandingQ  = useBrandingQuery();
  const updateM    = useUpdateBranding();
  const setBranding = useBrandingStore((s) => s.setBranding);

  const [form, setForm] = useState<BrandingUpdateRequest>({});
  const [dirty, setDirty] = useState(false);

  // Initialize form when data loads
  useEffect(() => {
    if (brandingQ.data && !dirty) {
      setForm({
        nombre_comercial:  brandingQ.data.nombre_comercial,
        nicho:             brandingQ.data.nicho,
        logo_url:          brandingQ.data.logo_url,
        color_primary:     brandingQ.data.color_primary,
        color_secondary:   brandingQ.data.color_secondary,
        color_accent:      brandingQ.data.color_accent,
        tema:              brandingQ.data.tema,
        tipografia:        brandingQ.data.tipografia,
        categorias_default: brandingQ.data.categorias_default,
      });
    }
  }, [brandingQ.data, dirty]);

  function patch(updates: Partial<BrandingUpdateRequest>) {
    setForm((f) => ({ ...f, ...updates }));
    setDirty(true);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    try {
      const updated = await updateM.mutateAsync(form);
      setBranding(updated);
      setDirty(false);
    } catch {
      /* toast en hook */
    }
  }

  if (!canEdit) {
    return (
      <div className="flex h-full items-center justify-center p-12">
        <Card>
          <CardContent className="space-y-2 p-10 text-center">
            <Palette className="mx-auto h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm font-medium">Acceso restringido</p>
            <p className="text-xs text-muted-foreground">
              Solo el owner puede editar el branding.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Branding</h1>
          <p className="text-sm text-muted-foreground">
            Personaliza la identidad visual de tu negocio.
          </p>
        </div>
        <Button
          form="branding-form"
          type="submit"
          disabled={!dirty || updateM.isPending}
        >
          {updateM.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Guardar cambios
        </Button>
      </header>

      {brandingQ.isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-96 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      ) : (
        <form id="branding-form" onSubmit={handleSave}>
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Left: Fields */}
            <div className="space-y-4">
              {/* Identidad */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Identidad del negocio</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1">
                    <Label htmlFor="b-nombre">Nombre comercial *</Label>
                    <Input
                      id="b-nombre"
                      value={form.nombre_comercial ?? ""}
                      onChange={(e) => patch({ nombre_comercial: e.target.value })}
                      placeholder="Mi Restaurante"
                      disabled={updateM.isPending}
                    />
                  </div>

                  <div className="space-y-1">
                    <Label>Tipo de negocio</Label>
                    <Select
                      value={form.nicho ?? "restaurante"}
                      onValueChange={(v) => patch({ nicho: v })}
                      disabled={updateM.isPending}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {NICHOS.map((n) => (
                          <SelectItem key={n.value} value={n.value}>{n.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1">
                    <Label htmlFor="b-logo">URL del logo</Label>
                    <Input
                      id="b-logo"
                      value={form.logo_url ?? ""}
                      onChange={(e) => patch({ logo_url: e.target.value || null })}
                      placeholder="https://cdn.example.com/logo.png"
                      disabled={updateM.isPending}
                    />
                    <p className="text-xs text-muted-foreground">
                      URL externa (Cloudinary, S3, etc.). Si está vacío, se muestra el logo Orion.
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Colores */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Colores</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(
                    [
                      { key: "color_primary",   label: "Color primario"   },
                      { key: "color_secondary", label: "Color secundario" },
                      { key: "color_accent",    label: "Color de acento"  },
                    ] as const
                  ).map(({ key, label }) => (
                    <div key={key} className="flex items-center gap-3">
                      <input
                        type="color"
                        value={(form[key] as string) ?? "#1f4ed8"}
                        onChange={(e) => patch({ [key]: e.target.value })}
                        disabled={updateM.isPending}
                        className="h-10 w-10 cursor-pointer rounded border border-border"
                      />
                      <div className="flex-1">
                        <Label>{label}</Label>
                        <Input
                          value={(form[key] as string) ?? ""}
                          onChange={(e) => patch({ [key]: e.target.value })}
                          placeholder="#1f4ed8"
                          disabled={updateM.isPending}
                          className="mt-1 h-8 font-mono text-xs"
                        />
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Tema y tipografía */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Apariencia</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1">
                    <Label>Tema</Label>
                    <Select
                      value={form.tema ?? "dark"}
                      onValueChange={(v) => patch({ tema: v as BrandingTema })}
                      disabled={updateM.isPending}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {TEMAS.map((t) => (
                          <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1">
                    <Label>Tipografía</Label>
                    <Select
                      value={form.tipografia ?? "Inter"}
                      onValueChange={(v) => patch({ tipografia: v })}
                      disabled={updateM.isPending}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {TIPOGRAFIAS.map((t) => (
                          <SelectItem key={t} value={t}>{t}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right: Live Preview */}
            <div className="space-y-4">
              <Card className="sticky top-20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Eye className="h-4 w-4" />
                    Preview en vivo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <BrandingPreview form={form} />
                </CardContent>
              </Card>
            </div>
          </div>
        </form>
      )}
    </div>
  );
}

// ─── Live Preview ─────────────────────────────────────────────────────────────
function BrandingPreview({ form }: { form: BrandingUpdateRequest }) {
  const primary   = form.color_primary   ?? "#1f4ed8";
  const secondary = form.color_secondary ?? "#1a1714";
  const accent    = form.color_accent    ?? "#22c55e";
  const nombre    = form.nombre_comercial ?? "Mi Negocio";

  return (
    <div className="overflow-hidden rounded-lg border text-xs">
      {/* Mini Sidebar */}
      <div className="flex h-56">
        <div
          className="flex w-32 flex-col gap-1 p-2"
          style={{ background: secondary }}
        >
          {/* Logo */}
          <div className="mb-2 flex items-center gap-1.5">
            {form.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={form.logo_url} alt="logo" className="h-5 w-5 rounded object-contain" />
            ) : (
              <div className="h-5 w-5 rounded" style={{ background: primary }} />
            )}
            <span className="truncate font-semibold text-white text-[10px]">
              {nombre}
            </span>
          </div>
          {/* Nav items */}
          {["Dashboard", "POS", "Productos", "Inventario"].map((item, i) => (
            <div
              key={item}
              className="rounded px-2 py-1"
              style={
                i === 0
                  ? { background: `${primary}33`, color: primary }
                  : { color: "#ffffff80" }
              }
            >
              {item}
            </div>
          ))}
        </div>

        {/* Main content */}
        <div className="flex-1 space-y-2 bg-card p-3">
          {/* Topbar */}
          <div className="flex items-center justify-between rounded border bg-muted/30 px-2 py-1">
            <span className="text-muted-foreground">Dashboard</span>
            <div className="h-4 w-4 rounded-full" style={{ background: primary }} />
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-2 gap-1.5">
            {[
              { l: "Ventas", v: "$1.200.000" },
              { l: "Órdenes",  v: "42"  },
            ].map(({ l, v }) => (
              <div key={l} className="rounded border bg-card p-1.5">
                <p className="text-muted-foreground" style={{ fontSize: 9 }}>{l}</p>
                <p className="font-bold" style={{ color: primary }}>{v}</p>
              </div>
            ))}
          </div>

          {/* Product card */}
          <div className="rounded border bg-card p-2">
            <p className="font-medium" style={{ fontSize: 9 }}>Bandeja Paisa</p>
            <p className="text-muted-foreground" style={{ fontSize: 8 }}>$35.000 · 8 ud</p>
            <div
              className="mt-1 rounded px-1.5 py-0.5 text-center font-semibold text-white"
              style={{ background: accent, fontSize: 8 }}
            >
              + Agregar
            </div>
          </div>
        </div>
      </div>

      {/* Color swatches */}
      <div className="flex h-6">
        {[primary, secondary, accent].map((c) => (
          <div key={c} className="flex-1" style={{ background: c }} />
        ))}
      </div>
    </div>
  );
}
