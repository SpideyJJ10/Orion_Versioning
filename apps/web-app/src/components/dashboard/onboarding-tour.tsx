"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  Circle,
  ArrowRight,
  Sparkles,
  X,
  ChevronDown,
  ChevronUp,
  Package,
  Boxes,
  ShoppingCart,
  Receipt,
  HelpCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

export interface TourStep {
  id: string;
  title: string;
  description: string;
  href: string;
  icon: any;
  actionText: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    id: "productos",
    title: "1. Registra tus Productos o Servicios",
    description: "Crea tu catálogo con precios, categorías e imágenes para vender rápidamente.",
    href: "/productos",
    icon: Package,
    actionText: "Ir a Productos",
  },
  {
    id: "inventario",
    title: "2. Ajusta tu Inventario Inicial",
    description: "Define las existencias iniciales y alertas de stock crítico para tus productos.",
    href: "/inventario",
    icon: Boxes,
    actionText: "Ir a Inventario",
  },
  {
    id: "pos",
    title: "3. Haz tu Primera Venta en el POS",
    description: "Abre el Punto de Venta táctil, agrega items al carrito y realiza un cobro de prueba.",
    href: "/pos",
    icon: ShoppingCart,
    actionText: "Abrir POS",
  },
  {
    id: "reportes",
    title: "4. Realiza el Arqueo & Cierre de Caja",
    description: "Consulta los reportes diarios y ejecuta el cuadre de caja con PIN de administrador.",
    href: "/reportes",
    icon: Receipt,
    actionText: "Ver Cierre de Caja",
  },
];

export function OnboardingTour() {
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  // Cargar estado de localStorage
  useEffect(() => {
    try {
      const savedCompleted = localStorage.getItem("orion_tour_completed");
      if (savedCompleted) setCompletedSteps(JSON.parse(savedCompleted));

      const savedDismissed = localStorage.getItem("orion_tour_dismissed");
      if (savedDismissed === "true") setIsDismissed(true);
    } catch (_) {}
  }, []);

  const toggleStep = (id: string) => {
    const updated = completedSteps.includes(id)
      ? completedSteps.filter((s) => s !== id)
      : [...completedSteps, id];

    setCompletedSteps(updated);
    try {
      localStorage.setItem("orion_tour_completed", JSON.stringify(updated));
    } catch (_) {}
  };

  const handleDismiss = () => {
    setIsDismissed(true);
    try {
      localStorage.setItem("orion_tour_dismissed", "true");
    } catch (_) {}
  };

  const handleReopen = () => {
    setIsDismissed(false);
    setIsMinimized(false);
    try {
      localStorage.removeItem("orion_tour_dismissed");
    } catch (_) {}
  };

  const progressPercent = Math.round((completedSteps.length / TOUR_STEPS.length) * 100);

  if (isDismissed) {
    return (
      <div className="flex justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={handleReopen}
          className="text-xs font-bold gap-2 border-primary/30 text-primary hover:bg-primary/10"
        >
          <HelpCircle className="h-4 w-4" />
          Ver Guía de Inicio Rápido ({completedSteps.length}/4)
        </Button>
      </div>
    );
  }

  return (
    <Card className="border-2 border-primary/30 bg-gradient-to-r from-primary/5 via-card to-background shadow-md overflow-hidden relative transition-all">
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-2xl gradient-orion flex items-center justify-center text-white shadow-md">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg font-black tracking-tight">
                Guía de Inicio Rápido
              </CardTitle>
              <Badge variant="outline" className="text-[10px] font-bold border-primary text-primary bg-primary/10">
                {progressPercent}% Completado
              </Badge>
            </div>
            <CardDescription className="text-xs">
              Sigue estos 4 sencillos pasos para dejar tu negocio listo para operar al 100%.
            </CardDescription>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
            onClick={() => setIsMinimized(!isMinimized)}
            title={isMinimized ? "Expandir guía" : "Minimizar guía"}
          >
            {isMinimized ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-destructive"
            onClick={handleDismiss}
            title="Ocultar guía de inicio"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      {!isMinimized && (
        <CardContent className="space-y-4 pt-1">
          {/* Barra de progreso */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-bold text-muted-foreground">
              <span>Progreso de configuración</span>
              <span>{completedSteps.length} de {TOUR_STEPS.length} pasos listos</span>
            </div>
            <Progress value={progressPercent} className="h-2 bg-muted" />
          </div>

          {/* Lista de pasos */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
            {TOUR_STEPS.map((step) => {
              const isDone = completedSteps.includes(step.id);
              const StepIcon = step.icon;

              return (
                <div
                  key={step.id}
                  className={`flex flex-col justify-between p-4 rounded-xl border transition-all ${
                    isDone
                      ? "border-success/30 bg-success/5 text-foreground"
                      : "border-border bg-card/60 hover:border-primary/40"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <button
                      type="button"
                      onClick={() => toggleStep(step.id)}
                      className="mt-0.5 text-muted-foreground hover:text-primary transition-colors shrink-0"
                      title={isDone ? "Marcar como pendiente" : "Marcar como listo"}
                    >
                      {isDone ? (
                        <CheckCircle2 className="h-5 w-5 text-success fill-success/20" />
                      ) : (
                        <Circle className="h-5 w-5 text-muted-foreground" />
                      )}
                    </button>

                    <div className="space-y-1 min-w-0">
                      <p className={`text-sm font-bold leading-none ${isDone ? "line-through text-muted-foreground" : "text-foreground"}`}>
                        {step.title}
                      </p>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {step.description}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 flex justify-end">
                    <Button asChild variant={isDone ? "ghost" : "outline"} size="sm" className="h-8 text-xs font-bold gap-1">
                      <Link href={step.href}>
                        {step.actionText}
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
