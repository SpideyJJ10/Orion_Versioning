"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
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
  Menu,
  MoreVertical,
  Settings,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useBrandingStore } from "@/lib/stores/branding-store";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { OrionLogo } from "@/components/brand/orion-logo";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  const router = useRouter();
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
        "hidden flex-col border-r bg-card md:flex select-none transition-all duration-300 relative shadow-sm",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Header / Logo + Botón de 3 Barras (Hamburger Menu) */}
      <div className="flex h-16 items-center justify-between border-b px-3">
        <div className="flex items-center gap-3 overflow-hidden px-1">
          <OrionLogo variant="mark" size="md" tenantLogoUrl={branding?.logo_url} />
          {!isCollapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-black tracking-tight">
                {branding?.nombre_comercial || "Orion POS"}
              </p>
              <p className="truncate text-[10px] text-muted-foreground capitalize font-semibold">
                {branding?.nicho || "Negocio"}
              </p>
            </div>
          )}
        </div>

        {/* Botón de 3 Barras (Menu Toggle) */}
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 text-muted-foreground hover:text-foreground hover:bg-muted/60 shrink-0 transition-transform active:scale-95"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? "Expandir menú de navegación" : "Colapsar menú"}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </div>

      {/* Navigation Groups with Dropdown Accordion */}
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
              <div key={group.id} className="space-y-1 py-1 border-b border-border/30 last:border-b-0">
                {visibleItems.map((item) => {
                  const ItemIcon = item.icon;
                  const active = pathname === item.href || pathname?.startsWith(item.href + "/");
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      title={item.label}
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-xl mx-auto transition-all duration-200",
                        active
                          ? "gradient-orion text-white shadow-md scale-105"
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
              {/* Dropdown Header Trigger */}
              <button
                type="button"
                onClick={() => toggleGroup(group.id)}
                className={cn(
                  "flex w-full items-center justify-between rounded-xl px-3 py-2 text-xs font-black uppercase tracking-wider transition-colors",
                  isGroupActive
                    ? "text-primary bg-primary/10"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                )}
              >
                <div className="flex items-center gap-2.5">
                  <GroupIcon className="h-4 w-4" />
                  <span>{group.label}</span>
                </div>
                {isOpen ? (
                  <ChevronDown className="h-4 w-4 transition-transform duration-200" />
                ) : (
                  <ChevronRight className="h-4 w-4 transition-transform duration-200" />
                )}
              </button>

              {/* Sub-menu Dropdown List */}
              {isOpen && (
                <div className="ml-3 space-y-1 border-l-2 border-primary/20 pl-2">
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
                            ? "gradient-orion text-white font-bold shadow-md transform translate-x-0.5"
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

      {/* Profile Card & Options Dropdown (3 Dots) */}
      <div className="p-2 space-y-2">
        {!isCollapsed ? (
          <div className="flex items-center justify-between gap-2 rounded-xl border bg-muted/30 p-2">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="flex h-9 w-9 items-center justify-center rounded-full gradient-orion text-sm font-bold text-white shadow-sm shrink-0">
                {(user?.nombre || "U").charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-bold text-foreground">{user?.nombre || "Usuario"}</p>
                <p className="truncate text-[10px] text-muted-foreground capitalize font-semibold">{user?.rol}</p>
              </div>
            </div>

            {/* Menu de 3 Puntos */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground shrink-0">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel className="text-xs">Mi Cuenta</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => router.push("/branding")} className="text-xs gap-2">
                  <Settings className="h-3.5 w-3.5 text-muted-foreground" />
                  Ajustes de Marca
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push("/usuarios")} className="text-xs gap-2">
                  <UserCheck className="h-3.5 w-3.5 text-muted-foreground" />
                  Equipo & Permisos
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => logout()} className="text-xs gap-2 text-destructive font-semibold">
                  <LogOut className="h-3.5 w-3.5" />
                  Cerrar sesión
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ) : (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10 mx-auto flex items-center justify-center rounded-full gradient-orion text-white font-bold shadow-md"
              >
                {(user?.nombre || "U").charAt(0).toUpperCase()}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-48">
              <DropdownMenuLabel className="text-xs truncate">{user?.nombre || "Usuario"}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push("/dashboard")} className="text-xs gap-2">
                <Home className="h-3.5 w-3.5" />
                Dashboard
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => logout()} className="text-xs gap-2 text-destructive font-semibold">
                <LogOut className="h-3.5 w-3.5" />
                Cerrar sesión
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </aside>
  );
}
