"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, LogOut, Settings, ChevronRight } from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useBrandingStore } from "@/lib/stores/branding-store";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetHeader } from "@/components/ui/sheet";
import { NAV_ITEMS, type NavItem } from "./sidebar";
import { cn } from "@/lib/utils";
import { OrionLogo } from "@/components/brand/orion-logo";
import { Separator } from "@/components/ui/separator";

export function Topbar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const { branding } = useBrandingStore();
  
  // Breadcrumbs logic
  const currentItem = NAV_ITEMS.find((item: NavItem) => 
    pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href + "/"))
  );
  
  const visibleItems = NAV_ITEMS.filter(
    (item: NavItem) => !item.roles || (user && item.roles.includes(user.rol))
  );

  return (
    <header className="flex items-center justify-between px-4 md:px-6 py-3 border-b bg-background shadow-sm z-10 sticky top-0">
      <div className="flex items-center gap-3">
        {/* Mobile Nav Trigger */}
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 p-0 flex flex-col">
            <SheetHeader className="sr-only">
              <SheetTitle>Menú de navegación</SheetTitle>
            </SheetHeader>
            <div className="flex h-16 items-center gap-3 border-b px-5">
              <OrionLogo variant="mark" size="md" tenantLogoUrl={branding?.logo_url} />
              <div className="min-w-0 text-left">
                <p className="truncate text-sm font-semibold">{branding?.nombre_comercial || "Orion"}</p>
                <p className="truncate text-xs text-muted-foreground capitalize">{branding?.nicho || "Negocio"}</p>
              </div>
            </div>
            <nav className="flex-1 space-y-1 overflow-y-auto p-3">
              {visibleItems.map((item: NavItem) => {
                const Icon = item.icon;
                const active = pathname === item.href || pathname?.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <Separator />
            <div className="p-4">
              <Button variant="ghost" className="w-full justify-start text-destructive hover:text-destructive hover:bg-destructive/10" onClick={logout}>
                <LogOut className="mr-2 h-4 w-4" /> Cerrar sesión
              </Button>
            </div>
          </SheetContent>
        </Sheet>
        
        {/* Breadcrumbs */}
        <div className="hidden md:flex items-center gap-2 text-sm text-muted-foreground">
          <span className="font-medium">Orion</span>
          {currentItem && (
            <>
              <ChevronRight className="h-4 w-4" />
              <span className="text-foreground font-semibold">{currentItem.label}</span>
            </>
          )}
        </div>
        <div className="md:hidden text-sm font-semibold">
           {currentItem ? currentItem.label : "Orion"}
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-4">
        <div className="text-sm font-medium hidden sm:block">
          Hola, {user?.nombre || "Usuario"}
        </div>
        
        <Link href="/settings">
          <Button variant="ghost" size="icon" data-tour="topbar-menu">
            <Settings className="h-5 w-5" />
          </Button>
        </Link>
        
        <Button variant="ghost" size="icon" onClick={logout} className="hidden md:flex hover:text-destructive hover:bg-destructive/10">
          <LogOut className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
}
