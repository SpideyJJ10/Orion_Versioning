"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useBrandingQuery } from "@/lib/hooks/use-api";
import { useBrandingStore } from "@/lib/stores/branding-store";
import { api } from "@/lib/api";
import { OnboardingWizard } from "@/components/onboarding/wizard";

interface OnboardingProgress {
  perfil_configurado: boolean;
  primer_producto:    boolean;
  primera_venta:      boolean;
  saltado:            boolean;
  porcentaje:         number;
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router       = useRouter();
  const hydrated     = useAuthStore((s) => s.hydrated);
  const accessToken  = useAuthStore((s) => s.accessToken);
  const setBranding  = useBrandingStore((s) => s.setBranding);

  const [onboarding,       setOnboarding]       = useState<OnboardingProgress | null>(null);
  const [showOnboarding,   setShowOnboarding]   = useState(false);
  const [onboardingLoaded, setOnboardingLoaded] = useState(false);

  // Mientras hidratamos zustand desde localStorage, mostramos un fallback discreto
  useEffect(() => {
    if (hydrated && !accessToken) {
      router.replace("/login");
    }
  }, [hydrated, accessToken, router]);

  // Carga branding del tenant al autenticar (idempotente, refetch suave)
  const branding = useBrandingQuery({ enabled: !!accessToken });
  useEffect(() => {
    if (branding.data) setBranding(branding.data);
  }, [branding.data, setBranding]);

  // Carga el onboarding progress
  useEffect(() => {
    if (!accessToken || onboardingLoaded) return;
    setOnboardingLoaded(true);
    api
      .get<OnboardingProgress>("/api/v3/onboarding")
      .then((data) => {
        setOnboarding(data);
        // Mostrar si no está completo (< 100%) y no fue saltado
        if (!data.saltado && data.porcentaje < 100) {
          setShowOnboarding(true);
        }
      })
      .catch(() => {
        // No bloqueamos si falla
      });
  }, [accessToken, onboardingLoaded]);

  if (!hydrated) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!accessToken) return null; // Está redirigiendo

  return (
    <>
      {children}
      {showOnboarding && onboarding && (
        <OnboardingWizard
          progress={onboarding}
          onClose={() => setShowOnboarding(false)}
        />
      )}
    </>
  );
}
