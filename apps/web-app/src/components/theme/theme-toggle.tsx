"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useThemeStore, type ThemeMode } from "@/lib/stores/theme-store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const OPTIONS: { value: ThemeMode; label: string; Icon: typeof Sun }[] = [
  { value: "light",  label: "Claro",       Icon: Sun },
  { value: "dark",   label: "Oscuro",      Icon: Moon },
  { value: "system", label: "Sistema",     Icon: Monitor },
];

/**
 * Switch entre modos light / dark / system.
 *
 * Persistido en `localStorage` (`orion-theme`) y aplicado por el
 * `BrandingProvider`. El bootstrap inline en `<head>` (ver `app/layout.tsx`)
 * evita el flash de tema incorrecto en el primer paint.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const mode    = useThemeStore((s) => s.mode);
  const setMode = useThemeStore((s) => s.setMode);

  const Active = OPTIONS.find((o) => o.value === mode)?.Icon ?? Monitor;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn("h-9 w-9", className)}
          aria-label="Cambiar tema"
          title="Tema"
        >
          <Active className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40">
        {OPTIONS.map(({ value, label, Icon }) => (
          <DropdownMenuItem
            key={value}
            onClick={() => setMode(value)}
            className={cn(
              "gap-2",
              mode === value && "bg-accent/20 text-accent-foreground",
            )}
          >
            <Icon className="h-4 w-4" />
            <span>{label}</span>
            {mode === value && (
              <span className="ml-auto text-xs text-muted-foreground">activo</span>
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
