"use client";

import { useState, useEffect } from "react";
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
  ChevronDown,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
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
  href: string;
  icon: LucideIcon;
  roles?: Rol[];
}

export interface NavGroup {
  id: string;
  label: string;
  icon: LucideIcon;
  items: NavItem[];
  roles?: Rol[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    id: "analitica",
    label: "Analítica & Control",
    icon: ChartArea,
    items: [
      { label: "Dashboard", href: "/dashboard", icon: Home },
      { label: "Reportes & Cierre", href: "/reportes", icon: ChartArea, roles: ["owner", "manager", "super_admin"] },
      { label: "Orion Intelligence", href: "/ml", icon: Brain, roles: ["owner", "manager", "super_admin"] },
    ],
  },
  {
    id: "operacion",
    label: "Ventas & Operación",
    icon: ShoppingCart,
    items: [
      { label: "Punto de Venta", href: "/pos", icon: ShoppingCart },
      { label: "Gestión de Mesas", href: "/mesas", icon: LayoutDashboard, roles: ["owner", "manager", "super_admin", "cajero"] },
    ],
  },
  {
    id: "catalogo",
    label: "Inventario & Menú",
    icon: Boxes,
    items: [
      { label: "Productos & Servicios", href: "/productos", icon: Package, roles: ["owner", "manager", "inventario", "super_admin"] },
      { label: "Control de Inventario", href: "/inventario", icon: Boxes, roles: ["owner", "manager", "inventario", "super_admin"] },
    ],
  },
  {
    id: "admin",
    label: "Administración",
    icon: Users,
    items: [
      { label: "Equipo de Trabajo", href: "/usuarios", icon: Users, roles: ["owner", "manager", "super_admin"] },
      { label: "Personalización", href: "/branding", icon: Palette, roles: ["owner", "super_admin"] },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const branding = useBrandingStore((s) => s.branding);

  const [isCollapsed, setIsCollapsed] = useState(false);

  // Auto-expand group that contains active path
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    NAV_GROUPS.forEach((group) => {
      const hasActive = group.items.some(
        (item) => pathname === item.href || pathname?.startsWith(item.href + "/")
      );
      initial[group.id] = hasActive || group.id === "analitica" || group.id === "operacion";
    });
    return initial;
  });

  useEffect(() => {
    NAV_GROUPS.forEach((group) => {
      const hasActive = group.items.some(
        (item) => pathname === item.href || pathname?.startsWith(item.href + "/")
      );
      if (hasActive) {
        setOpenGroups((prev) => ({ ...prev, [group.id]: true }));
      }
    });
  }, [pathname]);

  const toggleGroup = (groupId: string) => {
    if (isCollapsed) setIsCollapsed(false);
    setOpenGroups((prev) => ({ ...prev, [groupId]: !prev[groupId] }));
  };

  return (
    <aside
      className={cn(
        "hidden flex-col border-r bg-card md:flex select-none transition-all duration-300 relative",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Header / Tenant Logo + Toggle Button */}
      <div className="flex h-16 items-center justify-between border-b px-3">
        <div className="flex items-center gap-3 overflow-hidden px-1">
          <OrionLogo variant="mark" size="md" tenantLogoUrl={branding?.logo_url} />
          {!isCollapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold tracking-tight">
                {branding?.nombre_comercial || "Orion POS"}
              </p>
              <p className="truncate text-[10px] text-muted-foreground capitalize font-medium">
                {branding?.nicho || "Negocio"}
              </p>
            </div>
          )}
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-foreground shrink-0"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? "Expandir menú" : "Colapsar menú"}
        >
          {isCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </Button>
      </div>

      {/* Dropdown Navigation Menu */}
      <nav className="flex-1 space-y-2 overflow-y-auto p-2">
        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter(
            (item) => !item.roles || (user && item.roles.includes(user.rol))
          );

          if (visibleItems.length === 0) return null;

          const isGroupActive = visibleItems.some(
            (item) => pathname === item.href || pathname?.startsWith(item.href + "/")
          );
          const isOpen = openGroups[group.id] ?? false;
          const GroupIcon = group.icon;

          if (isCollapsed) {
            return (
              <div key={group.id} className="space-y-1 py-1">
                {visibleItems.map((item) => {
                  const ItemIcon = item.icon;
                  const active = pathname === item.href || pathname?.startsWith(item.href + "/");
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      title={item.label}
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-lg mx-auto transition-all",
                        active
                          ? "gradient-orion text-white shadow-md"
                          : "text-muted-foreground hover:bg-accent hover:text-foreground"
                      )}
                    >
                      <ItemIcon className="h-5 w-5" />
                    </Link>
                  );
                })}
              </div>
            );
          }

          return (
            <div key={group.id} className="space-y-1">
              {/* Group Header Dropdown Trigger */}
              <button
                type="button"
                onClick={() => toggleGroup(group.id)}
                className={cn(
                  "flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-bold uppercase tracking-wider transition-colors",
                  isGroupActive
                    ? "text-primary bg-primary/5"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                )}
              >
                <div className="flex items-center gap-2">
                  <GroupIcon className="h-4 w-4" />
                  <span>{group.label}</span>
                </div>
                {isOpen ? (
                  <ChevronDown className="h-3.5 w-3.5 transition-transform duration-200" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 transition-transform duration-200" />
                )}
              </button>

              {/* Sub-menu Items */}
              {isOpen && (
                <div className="ml-3 space-y-1 border-l border-border/50 pl-2">
                  {visibleItems.map((item) => {
                    const ItemIcon = item.icon;
                    const active = pathname === item.href || pathname?.startsWith(item.href + "/");

                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                          "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150",
                          active
                            ? "gradient-orion text-white font-bold shadow-md"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                        )}
                      >
                        <ItemIcon className="h-4 w-4 shrink-0" />
                        <span className="truncate">{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <Separator />

      {/* User Card & Logout */}
      <div className="p-2 space-y-2">
        {!isCollapsed ? (
          <>
            <div className="flex items-center gap-2.5 rounded-xl border bg-muted/20 p-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-full gradient-orion text-sm font-bold text-white shadow-sm shrink-0">
                {(user?.nombre || "U").charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-bold text-foreground">{user?.nombre || "Usuario"}</p>
                <p className="truncate text-[10px] text-muted-foreground capitalize font-medium">{user?.rol}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-xs text-muted-foreground hover:text-destructive"
              onClick={() => logout()}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Cerrar sesión
            </Button>
          </>
        ) : (
          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10 mx-auto flex items-center justify-center text-muted-foreground hover:text-destructive"
            onClick={() => logout()}
            title="Cerrar sesión"
          >
            <LogOut className="h-5 w-5" />
          </Button>
        )}
      </div>
    </aside>
  );
}
