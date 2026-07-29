import { AuthGuard } from "@/components/auth/auth-guard";
import { Sidebar } from "@/components/layout/sidebar";

/**
 * Layout protegido: rodea todas las páginas en `/(app)/*`.
 * - Verifica autenticación (redirige a /login si no hay token).
 * - Carga branding del tenant.
 * - Renderiza sidebar + área principal.
 */
export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar />
        <main className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">{children}</div>
        </main>
      </div>
    </AuthGuard>
  );
}
