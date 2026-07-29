"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Plus, Trash2 } from "lucide-react";

import { negocioApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/lib/stores/auth-store";

export default function PaymentMethodsPage() {
  const [methods, setMethods] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newMethod, setNewMethod] = useState("");
  const { hasRole } = useAuthStore();
  
  const canEdit = hasRole('owner', 'super_admin');

  useEffect(() => {
    loadMethods();
  }, []);

  async function loadMethods() {
    try {
      const data = await negocioApi.getMetodosPago();
      setMethods(data);
    } catch (error) {
      toast.error("Error al cargar métodos de pago");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(newMethodsList: string[]) {
    if (!canEdit) return;
    setSaving(true);
    try {
      const data = await negocioApi.updateMetodosPago(newMethodsList);
      setMethods(data);
      toast.success("Métodos de pago actualizados");
    } catch (error) {
      toast.error("Error al actualizar");
    } finally {
      setSaving(false);
    }
  }

  function handleAdd() {
    const method = newMethod.trim();
    if (!method) return;
    if (methods.includes(method)) {
      toast.error("El método ya existe");
      return;
    }
    const updated = [...methods, method];
    setMethods(updated);
    setNewMethod("");
    handleSave(updated);
  }

  function handleRemove(methodToRemove: string) {
    const updated = methods.filter((m) => m !== methodToRemove);
    setMethods(updated);
    handleSave(updated);
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Métodos de Pago</h1>
        <p className="text-muted-foreground">
          Configura los métodos de pago que aceptas en tu negocio.
        </p>
      </div>

      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Métodos Aceptados</CardTitle>
          <CardDescription>
            Estos métodos aparecerán al momento de procesar una venta o cobrar una orden.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="space-y-2">
            {methods.map((method) => (
              <li
                key={method}
                className="flex items-center justify-between rounded-md border p-3 shadow-sm"
              >
                <span className="font-medium">{method}</span>
                {canEdit && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive"
                    onClick={() => handleRemove(method)}
                    disabled={saving}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </li>
            ))}
          </ul>

          {methods.length === 0 && (
            <p className="text-sm text-muted-foreground">No hay métodos de pago configurados.</p>
          )}

          {canEdit && (
            <div className="flex gap-2 pt-4">
              <Input
                placeholder="Ej. Nequi, Daviplata, Cripto..."
                value={newMethod}
                onChange={(e) => setNewMethod(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleAdd();
                }}
                disabled={saving}
              />
              <Button onClick={handleAdd} disabled={saving || !newMethod.trim()}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                <span className="ml-2">Agregar</span>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
