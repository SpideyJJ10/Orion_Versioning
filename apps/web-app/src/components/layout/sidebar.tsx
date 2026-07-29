"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Boxes,
  Brain,
  ChartArea,
  Home,
  LogOut,
  Package,
  Palette,
  ShoppingCart,
  Users,
  LayoutDashboard,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useBrandingStore } from "@/lib/stores/branding-store";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { OrionLogo } from "@/components/brand/orion-logo";
import type { Rol } from "@/lib/api/types";

export interface NavItem {
  label: string;
  href:  string;
  icon:  LucideIcon;
  roles?: Rol[]; // Si se omite, todos los roles autenticados
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard",  href: "/dashboard",  icon: Home },
  { label: "POS",        href: "/pos",        icon: ShoppingCart },
  { label: "Mesas",      href: "/mesas",      icon: LayoutDashboard,
    roles: ["owner", "manager", "super_admin", "cajero"] },
  { label: "Inventario", href: "/inventario", icon: Boxes,
    roles: ["owner", "manager", "inventario", "super_admin"] },
  { label: "Productos",  href: "/productos",  icon: Package,
    roles: ["owner", "manager", "inventario", "super_admin"] },
  { label: "Reportes",   href: "/reportes",   icon: ChartArea,
    roles: ["owner", "manager", "super_admin"] },
  { label: "Inteligencia", href: "/ml",       icon: Brain,
    roles: ["owner", "manager", "super_admin"] },
  { label: "Equipo",     href: "/usuarios",   icon: Users,
    roles: ["owner", "manager", "super_admin"] },
  { label: "Branding",   href: "/branding",   icon: Palette,
    roles: ["owner", "super_admin"] },
];

export function Sidebar() {
  const pathname = usePathname();
  const user     = useAuthStore((s) => s.user);
  const logout   = useAuthStore((s) => s.logout);
  const branding = useBrandingStore((s) => s.branding);

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || (user && item.roles.includes(user.rol))
  );

  return (
    <aside className="hidden w-64 flex-col border-r bg-card md:flex">
      {/* Logo + nombre del tenant (white-label) */}
      <div className="flex h-16 items-center gap-3 border-b px-5">
        <OrionLogo
          variant="mark"
          size="md"
          tenantLogoUrl={branding?.logo_url}
        />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">
            {branding?.nombre_comercial || "Orion POS"}
          </p>
          <p className="truncate text-xs text-muted-foreground capitalize">
            {branding?.nicho || "Negocio"}
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {visibleItems.map((item) => {
          const Icon   = item.icon;
          const active = pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <Separator />

      {/* User & logout */}
      <div className="space-y-2 p-3">
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
            {(user?.nombre || "U").charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium">{user?.nombre || "Usuario"}</p>
            <p className="truncate text-xs text-muted-foreground capitalize">{user?.rol}</p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start"
          onClick={() => logout()}
        >
          <LogOut className="h-4 w-4" />
          Cerrar sesión
        </Button>
      </div>
    </aside>
  );
}
