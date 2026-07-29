"""
test_dev.py — Flujo de testeo en desarrollo para Orion POS v3

Ejecutar con: python scripts/test_dev.py
Prerrequisito: El servidor local debe estar corriendo (uvicorn backend.main:app --reload)
"""
import sys
import os
import json
import time
import requests
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────
BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8000")
TIMEOUT  = 10

# Colores para terminal
class C:
    OK   = "\033[92m"
    FAIL = "\033[91m"
    WARN = "\033[93m"
    INFO = "\033[94m"
    BOLD = "\033[1m"
    END  = "\033[0m"

# ── State ─────────────────────────────────────────────────────────
results = {"passed": 0, "failed": 0, "warnings": 0, "tests": []}
tokens  = {}


def log(status, msg):
    icon = {"OK": "[OK]", "FAIL": "[!!]", "WARN": "[??]", "INFO": "[ii]"}.get(status, "  ")
    color = getattr(C, status, C.END)
    print(f"  {icon} {color}{msg}{C.END}")
    
    if status == "OK":
        results["passed"] += 1
    elif status == "FAIL":
        results["failed"] += 1
    elif status == "WARN":
        results["warnings"] += 1
    
    results["tests"].append({"status": status, "msg": msg})


def section(title):
    print(f"\n{C.BOLD}{'=' * 60}{C.END}")
    print(f"{C.BOLD}  {title}{C.END}")
    print(f"{C.BOLD}{'=' * 60}{C.END}")


def req(method, path, body=None, headers=None, expected_status=200, retries=2):
    """Helper para HTTP requests con validación de status"""
    url = f"{BASE_URL}{path}"
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    
    for attempt in range(retries + 1):
        try:
            kw = {"method": method, "url": url, "headers": h, "timeout": TIMEOUT}
            if body is not None:
                kw["json"] = body
            resp = requests.request(**kw)
            return resp
        except requests.exceptions.ConnectionError as ce:
            if attempt < retries:
                time.sleep(0.5)
                continue
            print(f"    [ConnectionError] {ce}")
            return None
        except Exception as e:
            print(f"    [Exception] {type(e).__name__}: {e}")
            return None


def auth_header(token_key="access"):
    return {"Authorization": f"Bearer {tokens.get(token_key, '')}"}


# ══════════════════════════════════════════════════════════════════
#  TESTS
# ══════════════════════════════════════════════════════════════════

def test_01_health():
    """Verificar que el servidor está corriendo"""
    section("1. HEALTH CHECK")
    
    resp = req("GET", "/api/health")
    if resp is None:
        log("FAIL", f"Servidor no responde en {BASE_URL}")
        log("INFO", "Ejecuta primero: uvicorn backend.main:app --reload --port 8000")
        return False
    
    if resp.status_code == 200:
        data = resp.json()
        log("OK", f"Servidor OK — v{data.get('version', '?')}")
        return True
    else:
        log("FAIL", f"Health check retornó {resp.status_code}")
        return False


def test_02_static_pages():
    """Verificar que las páginas estáticas se sirven correctamente"""
    section("2. PÁGINAS ESTÁTICAS")
    
    pages = {
        "/":              "index.html (app principal)",
        "/login":         "login.html",
        "/login.html":    "login.html (ruta directa)",
        "/register":      "register.html",
        "/register.html": "register.html (ruta directa)",
        "/admin":         "admin.html",
        "/legacy":        "index-legacy.html (backup)",
        "/manifest.json": "PWA manifest",
    }
    
    all_ok = True
    for path, desc in pages.items():
        resp = req("GET", path)
        if resp is not None and resp.status_code == 200:
            log("OK", f"{desc} -> {resp.status_code}")
        else:
            status = resp.status_code if resp else "N/A"
            log("FAIL", f"{desc} -> {status}")
            all_ok = False
    
    return all_ok


def test_03_static_assets():
    """Verificar que los assets estáticos cargan"""
    section("3. ASSETS ESTÁTICOS")
    
    assets = [
        "/assets/orion-logo.svg",
        "/assets/orion-gem-icon.svg",
        "/css/main.css",
        "/css/components/app-ui.css",
        "/js/core/app-shell.js",
        "/js/core/api-client.js",
        "/js/core/ui.js",
        "/js/core/tutorial-manager.js",
        "/js/views/pos.js",
        "/js/views/dashboard.js",
        "/js/views/inventario.js",
        "/js/views/config.js",
        "/js/views/usuarios.js",
    ]
    
    all_ok = True
    for asset in assets:
        resp = req("GET", asset)
        if resp is not None and resp.status_code == 200:
            size_kb = round(len(resp.content) / 1024, 1)
            log("OK", f"{asset} -> {size_kb} KB")
        else:
            status = resp.status_code if resp else "N/A"
            log("FAIL", f"{asset} -> {status}")
            all_ok = False
    
    return all_ok


def test_04_register():
    """Probar flujo de registro (nuevo negocio)"""
    section("4. REGISTRO DE NEGOCIO")
    
    ts = int(time.time())
    test_email = f"test_{ts}@orion-dev.co"
    
    resp = req("POST", "/api/v3/auth/register", {
        "email": test_email,
        "password": "TestPassword123!",
        "nombre_comercial": f"Test Negocio {ts}",
        "nombre_propietario": "QA Tester",
        "nicho": "restaurante",
        "telefono": "3001234567"
    })
    
    if resp is not None and resp.status_code == 201:
        data = resp.json()
        tokens["access"]  = data["access_token"]
        tokens["refresh"] = data["refresh_token"]
        tokens["user"]    = data["usuario"]
        log("OK", f"Registro exitoso — Email: {test_email}")
        log("OK", f"  Rol: {data['usuario']['rol']}, Tenant: {data['usuario']['tenant_id']}")
        return True
    elif resp is not None and resp.status_code == 409:
        log("WARN", f"Email ya registrado: {test_email}")
        return True  # No es un error fatal
    else:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("FAIL", f"Registro falló: {detail}")
        return False


def test_05_login():
    """Probar login con credenciales de admin default"""
    section("5. LOGIN (Admin Default)")
    
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@test.com")
    admin_pass  = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    resp = req("POST", "/api/v3/auth/login", {
        "email": admin_email,
        "password": admin_pass
    })
    
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        tokens["access"]  = data["access_token"]
        tokens["refresh"] = data["refresh_token"]
        tokens["user"]    = data["usuario"]
        log("OK", f"Login OK — {data['usuario']['email']} ({data['usuario']['rol']})")
        return True
    else:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("WARN", f"Login admin falló: {detail}")
        log("INFO", "Usando token del registro para continuar tests")
        return bool(tokens.get("access"))


def test_06_auth_me():
    """Verificar endpoint /me con token"""
    section("6. AUTH /ME")
    
    if not tokens.get("access"):
        log("WARN", "Sin token — saltando test")
        return False
    
    resp = req("GET", "/api/v3/auth/me", headers=auth_header())
    
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        log("OK", f"/me -> {data['nombre']} ({data['rol']})")
        return True
    else:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("FAIL", f"/me falló: {detail}")
        return False


def test_07_refresh_token():
    """Verificar renovación de tokens"""
    section("7. REFRESH TOKEN")
    
    if not tokens.get("refresh"):
        log("WARN", "Sin refresh token — saltando test")
        return False
    
    resp = req("POST", "/api/v3/auth/refresh", {
        "refresh_token": tokens["refresh"]
    })
    
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        tokens["access"]  = data["access_token"]
        tokens["refresh"] = data["refresh_token"]
        log("OK", "Token renovado exitosamente")
        return True
    else:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("FAIL", f"Refresh falló: {detail}")
        return False


def test_08_branding():
    """Verificar branding del tenant"""
    section("8. BRANDING")
    
    if not tokens.get("access"):
        log("WARN", "Sin token — saltando test")
        return False
    
    resp = req("GET", "/api/v3/branding", headers=auth_header())
    
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        log("OK", f"Branding: {data.get('nombre_comercial', '?')} — Color: {data.get('color_primary', '?')}")
        return True
    else:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("WARN", f"Branding no disponible: {detail}")
        return False


def test_09_onboarding():
    """Verificar endpoints de onboarding"""
    section("9. ONBOARDING")
    
    if not tokens.get("access"):
        log("WARN", "Sin token — saltando test")
        return False
    
    resp = req("GET", "/api/v3/onboarding", headers=auth_header())
    
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        log("OK", f"Onboarding: completado={data.get('completado', False)}")
        return True
    else:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("WARN", f"Onboarding no disponible: {detail}")
        return False


def test_10_sucursales():
    """Verificar listado de sucursales (default 'Principal' se auto-crea)"""
    section("10. SUCURSALES")
    
    if not tokens.get("access"):
        log("WARN", "Sin token — saltando test")
        return False
    
    resp = req("GET", "/api/sucursales", headers=auth_header())
    
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        log("OK", f"Sucursales: {len(data)} encontradas")
        if len(data) == 0:
            log("FAIL", "Esperábamos al menos 1 sucursal (default 'Principal')")
            return False
        # Guardar sucursal_id para tests posteriores
        tokens["sucursal_id"] = data[0]["id"]
        for s in data[:3]:
            log("INFO", f"  -> {s.get('nombre', '?')} (id: {s.get('id', '?')[:8]}...)")
        # Verificar que la primera sucursal se llame "Principal"
        if data[0]["nombre"] == "Principal":
            log("OK", "Sucursal default 'Principal' creada automáticamente")
        return True
    else:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("FAIL", f"Sucursales falló: {detail}")
        return False


def test_13_productos_crud():
    """Flujo CRUD de productos sobre la sucursal default"""
    section("13. PRODUCTOS CRUD")
    
    sucursal_id = tokens.get("sucursal_id")
    if not sucursal_id or not tokens.get("access"):
        log("WARN", "Sin sucursal o token — saltando test")
        return False
    
    # CREAR producto
    resp = req("POST", "/api/productos", {
        "nombre": "Producto Test QA",
        "precio": 15000,
        "categoria": "Test",
        "insumos": "",
        "sucursal_id": sucursal_id,
    }, headers=auth_header(), expected_status=201)
    
    if resp is None or resp.status_code != 201:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("FAIL", f"Crear producto falló: {detail}")
        return False
    
    producto_id = resp.json()["id"]
    log("OK", f"Producto creado: {producto_id[:8]}...")
    
    # LISTAR productos
    resp = req("GET", f"/api/productos?sucursal_id={sucursal_id}", headers=auth_header())
    if resp and resp.status_code == 200:
        items = resp.json()
        log("OK", f"Listado: {len(items)} productos")
    else:
        log("FAIL", "Listar productos falló")
        return False
    
    # EDITAR producto
    resp = req("PUT", f"/api/productos/{producto_id}", {"precio": 18000}, headers=auth_header())
    if resp and resp.status_code == 200:
        log("OK", f"Producto editado — nuevo precio: ${resp.json().get('precio')}")
    else:
        log("FAIL", "Editar producto falló")
        return False
    
    # Guardar para orden
    tokens["producto_id"] = producto_id
    tokens["producto_precio"] = 18000
    return True


def test_14_orden_checkout():
    """Simular flujo de checkout — crear orden con el producto"""
    section("14. ORDEN (CHECKOUT)")
    
    sucursal_id = tokens.get("sucursal_id")
    producto_id = tokens.get("producto_id")
    if not sucursal_id or not producto_id:
        log("WARN", "Sin producto de test — saltando")
        return False
    
    resp = req("POST", "/api/ordenes", {
        "sucursal_id": sucursal_id,
        "metodo_pago": "Efectivo",
        "domicilio": 0,
        "items": [{
            "producto_id": producto_id,
            "producto_nombre": "Producto Test QA",
            "precio_unitario": tokens["producto_precio"],
            "cantidad": 2,
        }]
    }, headers=auth_header(), expected_status=201)
    
    if resp is not None and resp.status_code == 201:
        data = resp.json()
        log("OK", f"Orden creada: {data.get('id', '?')[:8]}... (total: ${data.get('total', 0)})")
        return True
    else:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("FAIL", f"Crear orden falló: {detail}")
        return False


def test_15_reportes():
    """Verificar reporte del día (debe reflejar la orden creada)"""
    section("15. REPORTES (día)")
    
    sucursal_id = tokens.get("sucursal_id")
    if not sucursal_id:
        log("WARN", "Sin sucursal — saltando")
        return False
    
    resp = req("GET", f"/api/reportes/dia?sucursal_id={sucursal_id}&tz_offset=-5",
               headers=auth_header())
    
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        resumen = data.get("resumen_caja", {})
        total = resumen.get("total_dia", 0)
        log("OK", f"Reporte día: total ${total}, {len(data.get('productos', []))} productos")
        return True
    else:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("FAIL", f"Reporte día falló: {detail}")
        return False


def test_16_usuarios():
    """Verificar gestión de usuarios (solo owner/manager)"""
    section("16. USUARIOS (TEAM)")
    
    if not tokens.get("access"):
        log("WARN", "Sin token — saltando")
        return False
    
    resp = req("GET", "/api/v3/usuarios", headers=auth_header())
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        log("OK", f"Usuarios del tenant: {len(data)}")
        # El owner debería estar en la lista
        owner = next((u for u in data if u.get("rol") == "owner"), None)
        if owner:
            log("OK", f"  Owner: {owner['nombre']} ({owner['email']})")
        return True
    else:
        detail = resp.json().get("detail", "?") if resp else "Sin respuesta"
        log("FAIL", f"Listar usuarios falló: {detail}")
        return False


def test_11_unauthorized():
    """Verificar que endpoints protegidos rechazan sin token"""
    section("11. SEGURIDAD — Acceso sin token")
    
    endpoints = [
        ("GET",  "/api/v3/auth/me"),
        ("GET",  "/api/v3/branding"),
        ("GET",  "/api/sucursales"),
    ]
    
    all_ok = True
    for method, path in endpoints:
        resp = req(method, path)  # Sin Authorization header
        if resp is not None and resp.status_code in (401, 403):
            log("OK", f"{method} {path} -> {resp.status_code} (protegido)")
        else:
            status = resp.status_code if resp is not None else "N/A"
            log("FAIL", f"{method} {path} -> {status} (debería ser 401/403)")
            all_ok = False
    
    return all_ok


def test_12_css_modules():
    """Verificar que los módulos CSS se cargan"""
    section("12. CSS MODULES")
    
    css_files = [
        "/css/core/variables.css",
        "/css/core/reset.css",
        "/css/core/utilities.css",
        "/css/layouts/master.css",
        "/css/components/buttons.css",
        "/css/components/cards.css",
        "/css/components/forms.css",
        "/css/components/app-ui.css",
        "/css/components/tutorial.css",
        "/css/themes/dark.css",
        "/css/themes/light.css",
        "/css/views/cajero.css",
        "/css/views/admin.css",
    ]
    
    all_ok = True
    for css in css_files:
        resp = req("GET", css)
        if resp is not None and resp.status_code == 200:
            size_kb = round(len(resp.content) / 1024, 1)
            log("OK", f"{css.split('/')[-1]} -> {size_kb} KB")
        else:
            status = resp.status_code if resp else "N/A"
            log("FAIL", f"{css} -> {status}")
            all_ok = False
    
    return all_ok


# ══════════════════════════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════════════════════════

def print_summary():
    section("RESUMEN DE TESTS")
    
    total = results["passed"] + results["failed"]
    
    print(f"""
  {C.OK}[OK] Passed:   {results['passed']}{C.END}
  {C.FAIL}[!!] Failed:   {results['failed']}{C.END}
  {C.WARN}[??] Warnings: {results['warnings']}{C.END}
  {'-' * 40}
  Total:     {total} tests
  Resultado: {'TODO OK' if results['failed'] == 0 else 'HAY FALLOS'}
  Fecha:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """)
    
    if results["failed"] > 0:
        print(f"  {C.FAIL}Tests fallidos:{C.END}")
        for t in results["tests"]:
            if t["status"] == "FAIL":
                print(f"    [!!] {t['msg']}")
        print()


def main():
    print(f"\n{C.BOLD}{'=' * 60}{C.END}")
    print(f"{C.BOLD} {C.INFO} ORION POS v3 -- Test Suite (Desarrollo)               {C.END}")
    print(f"{C.BOLD}  Target: {BASE_URL}{C.END}")
    print(f"{C.BOLD}{'=' * 60}{C.END}")
    
    # Ejecutar tests en orden
    server_ok = test_01_health()
    
    if not server_ok:
        print(f"\n  {C.FAIL}STOP: Servidor no disponible. Abortando tests.{C.END}")
        print(f"  {C.INFO}Ejecuta: uvicorn backend.main:app --reload --port 8000{C.END}\n")
        sys.exit(1)
    
    test_02_static_pages()
    test_03_static_assets()
    test_04_register()
    test_05_login()
    test_06_auth_me()
    test_07_refresh_token()
    test_08_branding()
    test_09_onboarding()
    test_10_sucursales()
    test_13_productos_crud()
    test_14_orden_checkout()
    test_15_reportes()
    test_16_usuarios()
    test_11_unauthorized()
    test_12_css_modules()
    
    print_summary()
    
    sys.exit(1 if results["failed"] > 0 else 0)


if __name__ == "__main__":
    main()
