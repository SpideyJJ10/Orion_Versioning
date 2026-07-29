"use client";

import { useState } from "react";
import { Sparkles, Bot, Loader2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

import { aiApi } from "@/lib/api";
import type { AIConfigResponse } from "@/lib/api/ai";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { useAuthStore } from "@/lib/stores/auth-store";

export default function AISetupPage() {
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIConfigResponse["config"] | null>(null);
  const { hasRole } = useAuthStore();
  const isOwner = hasRole("owner");
  const router = useRouter();

  if (isOwner === false) {
    router.replace("/dashboard");
    return null;
  }

  async function handleGenerate() {
    if (!description.trim()) {
      toast.error("Por favor describe tu negocio.");
      return;
    }
    
    setLoading(true);
    setResult(null);

    try {
      const res = await aiApi.generatePOS(description);
      setResult(res.config);
      toast.success(res.message || "Configuración generada con éxito");
    } catch (error) {
      toast.error("Error al generar la plantilla. Verifica tu conexión o intenta con una descripción distinta.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Sparkles className="w-8 h-8 text-brand-500" />
          Configurador IA
        </h1>
        <p className="text-muted-foreground mt-2">
          Cuéntanos sobre tu negocio y nuestra Inteligencia Artificial configurará tu POS al instante.
        </p>
      </div>

      {!result ? (
        <Card className="border-brand-500/20 shadow-lg shadow-brand-500/5">
          <CardHeader>
            <CardTitle>Describe tu Negocio</CardTitle>
            <CardDescription>
              Ejemplo: "Tengo una pizzería artesanal italiana en Bogotá. Vendemos pizzas, pastas, bebidas y postres. Aceptamos efectivo, tarjetas y Nequi. Quiero colores cálidos y que llamen la atención."
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder="Describe tu negocio aquí..." 
              className="min-h-[150px] resize-y text-base"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={loading}
            />
          </CardContent>
          <CardFooter className="flex justify-end">
            <Button 
              onClick={handleGenerate} 
              disabled={loading || description.length < 10}
              className="bg-gradient-to-r from-brand-600 to-orange-500 hover:from-brand-500 hover:to-orange-400 text-white border-0"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analizando y Configurando...
                </>
              ) : (
                <>
                  <Bot className="w-4 h-4 mr-2" />
                  Generar Plantilla
                </>
              )}
            </Button>
          </CardFooter>
        </Card>
      ) : (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-400 p-4 rounded-lg flex items-center gap-3 border border-green-200 dark:border-green-900/50">
            <CheckCircle2 className="w-6 h-6" />
            <div>
              <p className="font-semibold">¡Tu POS ha sido configurado con éxito!</p>
              <p className="text-sm opacity-90">Hemos adaptado la plataforma a las necesidades de tu negocio.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Branding & Estilo</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between border-b pb-2">
                  <span className="text-muted-foreground">Nombre Comercial</span>
                  <span className="font-medium">{result.branding.nombre_comercial}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-muted-foreground">Nicho</span>
                  <span className="font-medium capitalize">{result.branding.nicho}</span>
                </div>
                <div className="flex justify-between pb-2">
                  <span className="text-muted-foreground">Colores</span>
                  <div className="flex gap-2">
                    <div className="w-5 h-5 rounded-full border shadow-sm" style={{ backgroundColor: result.branding.color_primary }} title="Primario" />
                    <div className="w-5 h-5 rounded-full border shadow-sm" style={{ backgroundColor: result.branding.color_secondary }} title="Secundario" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Métodos de Pago</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {result.metodos_pago.map((m) => (
                    <span key={m} className="px-2.5 py-1 bg-secondary text-secondary-foreground rounded-md text-sm font-medium">
                      {m}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="md:col-span-2">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Catálogo Inicial Creado ({result.productos_sugeridos.length} productos)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2 mb-4">
                  {result.categorias.map((c) => (
                    <span key={c} className="px-2.5 py-0.5 bg-brand-100 text-brand-800 dark:bg-brand-900/30 dark:text-brand-300 rounded-full text-xs font-semibold">
                      {c}
                    </span>
                  ))}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {result.productos_sugeridos.map((p, i) => (
                    <div key={i} className="border rounded-md p-3 flex justify-between items-center bg-card shadow-sm">
                      <div className="truncate pr-2">
                        <p className="font-medium text-sm truncate">{p.nombre}</p>
                        <p className="text-xs text-muted-foreground">{p.categoria}</p>
                      </div>
                      <div className="font-semibold text-sm whitespace-nowrap">
                        ${p.precio.toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="flex justify-end gap-4 mt-6">
            <Button variant="outline" onClick={() => setResult(null)}>
              Generar de Nuevo
            </Button>
            <Button onClick={() => router.push("/dashboard")}>
              Ir al Dashboard
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
