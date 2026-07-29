"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  ChevronRight,
  Package,
  ShoppingCart,
  Settings,
  X,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { OrionLogo } from "@/components/brand/orion-logo";
import { api } from "@/lib/api";

interface OnboardingProgress {
  perfil_configurado: boolean;
  primer_producto:    boolean;
  primera_venta:      boolean;
  saltado:            boolean;
  porcentaje:         number;
}

interface OnboardingWizardProps {
  progress: OnboardingProgress;
  onClose:  () => void;
}

const STEPS = [
  {
    id:          "perfil",
    icon:        Settings,
    title:       "Configura tu perfil",
    description: "Personaliza el nombre, colores y logo de tu negocio.",
    action:      "Ir a Branding",
    href:        "/branding",
    key:         "perfil_configurado" as keyof OnboardingProgress,
  },
  {
    id:          "producto",
    icon:        Package,
    title:       "Crea tu primer producto",
    description: "Agrega un producto al catálogo con precio y stock inicial.",
    action:      "Ir a Productos",
    href:        "/productos",
    key:         "primer_producto" as keyof OnboardingProgress,
  },
  {
    id:          "venta",
    icon:        ShoppingCart,
    title:       "Registra tu primera venta",
    description: "Abre el POS, agrega productos al carrito y cobra.",
    action:      "Abrir POS",
    href:        "/pos",
    key:         "primera_venta" as keyof OnboardingProgress,
  },
];

export function OnboardingWizard({ progress, onClose }: OnboardingWizardProps) {
  const [skipping, setSkipping] = useState(false);
  const router = useRouter();

  const completedCount = STEPS.filter((s) => progress[s.key]).length;
  const percentage     = Math.round((completedCount / STEPS.length) * 100);

  async function handleSkip() {
    setSkipping(true);
    try {
      await api.post("/api/v3/onboarding/skip", {});
    } catch {
      /* silencioso */
    } finally {
      setSkipping(false);
      onClose();
    }
  }

  function handleAction(href: string) {
    onClose();
    router.push(href);
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md [&>button:last-child]:hidden">
        <DialogHeader>
          <div className="mb-2 flex items-center justify-between">
            <OrionLogo variant="full" size="sm" />
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onClose}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <DialogTitle>¡Bienvenido a Orion!</DialogTitle>
          <DialogDescription>
            Completa estos 3 pasos para poner tu negocio en marcha.
          </DialogDescription>
        </DialogHeader>

        {/* Progress bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Progreso</span>
            <span className="font-semibold text-primary">{percentage}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-2">
          {STEPS.map((step) => {
            const done = !!progress[step.key];
            const Icon = step.icon;
            return (
              <div
                key={step.id}
                className={`flex flex-col sm:flex-row items-start sm:items-center gap-3 rounded-lg border p-3 transition-colors ${
                  done
                    ? "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/20"
                    : "border-border bg-card"
                }`}
              >
                {/* Number / Check */}
                <div className="flex w-full sm:w-auto items-center justify-between sm:justify-start gap-3">
                  <div
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                      done
                        ? "bg-green-500 text-white"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {done ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <Icon className="h-4 w-4" />
                    )}
                  </div>
                  
                  {/* CTA for mobile, moved next to number for flex-between */}
                  <div className="sm:hidden">
                    {!done && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="shrink-0"
                        onClick={() => handleAction(step.href)}
                      >
                        {step.action}
                        <ChevronRight className="ml-1 h-3 w-3" />
                      </Button>
                    )}
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 w-full mt-2 sm:mt-0">
                  <p className={`text-sm font-semibold ${done ? "line-through text-muted-foreground" : ""}`}>
                    {step.title}
                  </p>
                  <p className="text-xs text-muted-foreground">{step.description}</p>
                </div>

                {/* CTA Desktop */}
                <div className="hidden sm:block">
                  {!done && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="shrink-0"
                      onClick={() => handleAction(step.href)}
                    >
                      {step.action}
                      <ChevronRight className="ml-1 h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Skip */}
        <Button
          variant="ghost"
          size="sm"
          className="w-full text-muted-foreground"
          onClick={handleSkip}
          disabled={skipping}
        >
          Omitir tutorial
        </Button>
      </DialogContent>
    </Dialog>
  );
}
