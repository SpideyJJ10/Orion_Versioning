-- ── SUPABASE ROW LEVEL SECURITY (RLS) POLICIES FOR ORION MULTI-TENANCY ──
--
-- These policies enforce tenant-level isolation directly at the database layer (PostgreSQL).
-- They assume that the Supabase auth.users JWT contains the 'tenant_id' claim inside app_metadata.
-- 
-- Example JWT payload format expected:
-- {
--   "app_metadata": {
--     "tenant_id": 123
--   }
-- }
--
-- To set tenant_id in user's app_metadata from a trigger or custom function:
--   update auth.users set raw_app_meta_data = raw_app_meta_data || jsonb_build_object('tenant_id', 123) where id = ...;

-- Helper function to extract current tenant_id from the authenticated user JWT
CREATE OR REPLACE FUNCTION auth.current_tenant_id()
RETURNS integer
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(
    (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::integer,
    (auth.jwt() -> 'user_metadata' ->> 'tenant_id')::integer
  );
$$;

-- 1. TENANTS TABLE
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_self_access ON tenants
  FOR ALL
  TO authenticated
  USING (id = auth.current_tenant_id());

-- 2. SUCURSALES TABLE
ALTER TABLE sucursales ENABLE ROW LEVEL SECURITY;

CREATE POLICY sucursales_tenant_isolation ON sucursales
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.current_tenant_id());

-- 3. PRODUCTOS TABLE
ALTER TABLE productos ENABLE ROW LEVEL SECURITY;

CREATE POLICY productos_tenant_isolation ON productos
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.current_tenant_id());

-- 4. CATEGORIAS TABLE
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;

CREATE POLICY categorias_tenant_isolation ON categorias
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.current_tenant_id());

-- 5. ORDENES TABLE
ALTER TABLE ordenes ENABLE ROW LEVEL SECURITY;

CREATE POLICY ordenes_tenant_isolation ON ordenes
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.current_tenant_id());

-- 6. ORDEN_ITEMS TABLE
ALTER TABLE orden_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY orden_items_tenant_isolation ON orden_items
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.current_tenant_id());

-- 7. MOVIMIENTOS_INVENTARIO TABLE
ALTER TABLE movimientos_inventario ENABLE ROW LEVEL SECURITY;

CREATE POLICY movimientos_inventario_tenant_isolation ON movimientos_inventario
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.current_tenant_id());

-- 8. TENANT_BRANDING TABLE
ALTER TABLE tenant_branding ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_branding_tenant_isolation ON tenant_branding
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.current_tenant_id());

-- 9. USUARIOS TABLE
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;

CREATE POLICY usuarios_tenant_isolation ON usuarios
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.current_tenant_id());
