"""
scripts/seed_demo.py — Pueblo de datos demo con dos tenants y 60 días de operación.

Crea (o recrea, si --reset):
  • Tenant 1: "Asadero El Tizón" (restaurante, plan_activo=True)
       - 2 sucursales (Centro, Norte)
       - 12 productos en menu (entradas, principios, fuertes, bebidas)
       - Stock inicial alto + stock_minimo realista
       - 60 días de órdenes con patrones por hora del día y día semana

  • Tenant 2: "Farmacia La Esperanza" (retail, plan_activo=True)
       - 1 sucursal
       - 15 productos (medicinas, aseo)
       - 60 días de órdenes con patrón uniforme

Patrones simulados:
  • Restaurante: pico almuerzo (12-2pm) y cena (7-9pm); fin de semana +30%
  • Farmacia: distribución uniforme por hora; sin estacionalidad fuerte
  • Tendencia ligera al alza (+0.5% diario) para que ML pueda detectarla
  • Ruido gaussiano sobre demanda base

Uso:
    py -3 scripts/seed_demo.py                # crea solo si no existe
    py -3 scripts/seed_demo.py --reset        # borra los demos antes de crear
    py -3 scripts/seed_demo.py --days 90      # cambia el horizonte (default 60)

Credenciales generadas:
    demo@tizon.app   /  demo1234        (super owner del restaurante)
    demo@farmacia.co /  demo1234        (owner de la farmacia)
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running this script directly via `py -3 scripts/seed_demo.py`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Importar después de ajustar sys.path
from backend.auth_v3.passwords import hash_password  # noqa: E402
from backend.db.session import Base, SessionLocal, engine  # noqa: E402
from backend.models.orm import (  # noqa: E402
    Categoria,
    MovimientoInventario,
    OnboardingProgress,
    Orden,
    OrdenItem,
    Producto,
    Sucursal,
    Tenant,
    TenantBranding,
    Usuario,
)

# ─────────────────────────────────────────────────────────────────────────
#  CATALOGS — definiciones declarativas de cada tenant
# ─────────────────────────────────────────────────────────────────────────
RESTAURANTE = {
    "email":              "demo@tizon.app",
    "password":           "demo1234",
    "nombre":             "Asadero El Tizón",
    "propietario":        "Carlos Mendoza",
    "telefono":           "3015550101",
    "branding": {
        "nombre_comercial": "Asadero El Tizón",
        "color_primary":    "#8b5cf6",
        "color_secondary":  "#0f172a",
        "color_accent":     "#d946ef",
        "nicho":            "restaurante",
        "tema":             "dark",
        "tipografia":       "Inter",
        "categorias_default": ["Entradas", "Principios", "Fuertes", "Bebidas", "Postres"],
    },
    "sucursales": ["Centro", "Norte"],
    "productos": [
        # (nombre, precio, categoria, stock_inicial, stock_minimo, unidad, popularidad_relativa)
        ("Sopa de Costilla",       8000,  "Entradas",   60,  10, "unidad", 0.8),
        ("Empanadas (3 und)",      6000,  "Entradas",   80,  15, "unidad", 1.0),
        ("Arroz blanco",           3500,  "Principios", 100, 20, "unidad", 1.2),
        ("Frijoles",               4000,  "Principios", 90,  20, "unidad", 1.0),
        ("Bandeja Paisa",          25000, "Fuertes",    40,  8,  "unidad", 1.5),
        ("Lomo de res 250g",       28000, "Fuertes",    35,  6,  "unidad", 0.9),
        ("Pollo a la plancha",     22000, "Fuertes",    50,  8,  "unidad", 1.3),
        ("Pescado mojarra",        24000, "Fuertes",    25,  5,  "unidad", 0.6),
        ("Jugo natural",           5000,  "Bebidas",    120, 20, "unidad", 1.4),
        ("Gaseosa 350ml",          4000,  "Bebidas",    150, 30, "unidad", 1.6),
        ("Cerveza nacional",       6500,  "Bebidas",    96,  24, "unidad", 1.1),
        ("Postre de natas",        7000,  "Postres",    30,  6,  "unidad", 0.5),
    ],
    # Multiplicador de demanda por día (lun=0..dom=6)
    "demanda_dia": [0.9, 0.85, 0.85, 0.95, 1.10, 1.40, 1.30],
    # Multiplicador por hora (24 valores, 0..23)
    "demanda_hora": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0,    # 00-05
        0.0, 0.1, 0.3, 0.4, 0.5, 0.7,    # 06-11
        2.0, 2.2, 1.5, 0.6, 0.4, 0.5,    # 12-17 (pico almuerzo 12-13)
        1.4, 2.0, 1.8, 1.0, 0.4, 0.1,    # 18-23 (pico cena 19-20)
    ],
    "metodos_pago": [("Efectivo", 0.45), ("Nequi", 0.25), ("Daviplata", 0.10), ("Tarjeta", 0.20)],
    "ordenes_base_dia": 28,  # número aproximado de órdenes/día
    "items_por_orden": (1, 5),  # rango uniforme
    "domicilio_prob": 0.15,
    "domicilio_rango": (3000, 6000),
}


FARMACIA = {
    "email":              "demo@farmacia.co",
    "password":           "demo1234",
    "nombre":             "Farmacia La Esperanza",
    "propietario":        "María Restrepo",
    "telefono":           "3015550202",
    "branding": {
        "nombre_comercial": "Farmacia La Esperanza",
        "color_primary":    "#a855f7",
        "color_secondary":  "#0f172a",
        "color_accent":     "#ec4899",
        "nicho":            "farmacia",
        "tema":             "light",
        "tipografia":       "Roboto",
        "categorias_default": ["Medicamentos", "Cuidado personal", "Bebés", "Aseo"],
    },
    "sucursales": ["Sucursal Única"],
    "productos": [
        ("Acetaminofén x10",        4500,  "Medicamentos",     200, 40, "caja", 1.6),
        ("Ibuprofeno 400mg x10",    5500,  "Medicamentos",     180, 40, "caja", 1.4),
        ("Loratadina x10",          7000,  "Medicamentos",     90,  20, "caja", 0.9),
        ("Amoxicilina x14",         12000, "Medicamentos",     60,  15, "caja", 0.5),
        ("Vitamina C x30",          8500,  "Medicamentos",     100, 20, "caja", 1.0),
        ("Alcohol antiséptico 1L",  9000,  "Cuidado personal", 70,  15, "lt",   0.7),
        ("Algodón 50g",             4000,  "Cuidado personal", 120, 25, "pack", 0.8),
        ("Gel antibacterial 500ml", 6500,  "Cuidado personal", 110, 25, "ml",   1.1),
        ("Crema corporal 200ml",    11000, "Cuidado personal", 60,  12, "ml",   0.6),
        ("Pañales talla M (40 und)",32000, "Bebés",            45,  10, "pack", 1.0),
        ("Toallitas húmedas x80",   8000,  "Bebés",            80,  20, "pack", 0.9),
        ("Champú bebé 500ml",       14000, "Bebés",            50,  12, "ml",   0.5),
        ("Detergente líquido 1L",   12000, "Aseo",             80,  20, "lt",   1.0),
        ("Jabón en barra x3",       5000,  "Aseo",             140, 30, "pack", 1.2),
        ("Cloro 2L",                7500,  "Aseo",             70,  15, "lt",   0.7),
    ],
    "demanda_dia":  [1.0, 1.0, 1.0, 1.0, 1.05, 1.20, 0.80],
    "demanda_hora": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.1, 0.5, 1.0, 1.2, 1.3, 1.3,
        1.2, 1.0, 1.0, 1.1, 1.2, 1.3,
        1.4, 1.2, 0.9, 0.5, 0.2, 0.0,
    ],
    "metodos_pago": [("Efectivo", 0.55), ("Nequi", 0.20), ("Daviplata", 0.15), ("Tarjeta", 0.10)],
    "ordenes_base_dia": 45,
    "items_por_orden": (1, 3),
    "domicilio_prob": 0.05,
    "domicilio_rango": (2000, 4000),
}


# ─────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────
def _ponderar(opciones: list[tuple]) -> str:
    """Selecciona un valor de [(valor, peso), ...] usando pesos."""
    pesos = [p for _, p in opciones]
    valores = [v for v, _ in opciones]
    return random.choices(valores, weights=pesos, k=1)[0]


def _eliminar_tenant_si_existe(db, email: str) -> bool:
    """Borra el tenant y todos sus datos si existe. Retorna True si borró algo."""
    tenant = db.query(Tenant).filter_by(email=email).first()
    if not tenant:
        return False
    db.delete(tenant)  # cascade limpia todo
    db.commit()
    return True


def _crear_tenant(db, spec: dict) -> Tenant:
    pwd = hash_password(spec["password"])
    t = Tenant(
        email         = spec["email"],
        password_hash = pwd,
        nombre        = spec["nombre"],
        propietario   = spec["propietario"],
        telefono      = spec["telefono"],
        plan          = "starter",
        plan_activo   = True,
        es_admin      = False,
    )
    db.add(t)
    db.flush()

    # Branding
    bspec = spec["branding"]
    db.add(TenantBranding(
        tenant_id          = t.id,
        nombre_comercial   = bspec["nombre_comercial"],
        color_primary      = bspec["color_primary"],
        color_secondary    = bspec["color_secondary"],
        color_accent       = bspec["color_accent"],
        nicho              = bspec["nicho"],
        tema               = bspec["tema"],
        tipografia         = bspec["tipografia"],
        categorias_default = bspec["categorias_default"],
    ))

    # Onboarding ya completado (es demo)
    db.add(OnboardingProgress(
        tenant_id          = t.id,
        perfil_configurado = True,
        primer_producto    = True,
        primera_venta      = True,
        completado_en      = _utcnow(),
    ))

    # Sucursales
    sucursales: list[Sucursal] = []
    for nombre in spec["sucursales"]:
        s = Sucursal(tenant_id=t.id, nombre=nombre)
        db.add(s)
        sucursales.append(s)
    db.flush()

    # Owner usuario operativo (rol=owner) en la 1ra sucursal
    db.add(Usuario(
        tenant_id     = t.id,
        email         = spec["email"],
        password_hash = pwd,
        nombre        = spec["propietario"],
        rol           = "owner",
        sucursal_id   = sucursales[0].id,
        activo        = True,
    ))

    # Categorías + productos por sucursal
    for sucursal in sucursales:
        cats: dict[str, Categoria] = {}
        for cat_nombre in bspec["categorias_default"]:
            c = Categoria(tenant_id=t.id, sucursal_id=sucursal.id, nombre=cat_nombre)
            db.add(c)
            cats[cat_nombre] = c
        db.flush()

        for nombre, precio, cat, stock_ini, stock_min, unidad, _pop in spec["productos"]:
            cat_obj = cats.get(cat)
            p = Producto(
                tenant_id     = t.id,
                sucursal_id   = sucursal.id,
                nombre        = nombre,
                precio        = precio,
                insumos       = "",
                categoria     = cat,
                categoria_id  = cat_obj.id if cat_obj else None,
                stock         = stock_ini,
                stock_minimo  = stock_min,
                unidad_medida = unidad,
            )
            db.add(p)
            db.flush()
            # Movimiento de stock inicial
            db.add(MovimientoInventario(
                tenant_id     = t.id,
                sucursal_id   = sucursal.id,
                producto_id   = p.id,
                tipo          = "entrada",
                cantidad      = stock_ini,
                stock_antes   = 0,
                stock_despues = stock_ini,
                motivo        = "Stock inicial demo",
                referencia_id = None,
                usuario_id    = None,
            ))

    db.commit()
    db.refresh(t)
    return t


def _utcnow():
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────
#  GENERACIÓN DE ÓRDENES SINTÉTICAS
# ─────────────────────────────────────────────────────────────────────────
def _generar_ordenes_para_tenant(
    db,
    tenant: Tenant,
    spec: dict,
    *,
    dias: int,
    rng: random.Random,
):
    """Crea órdenes históricas con el patrón definido en `spec`.

    Estrategia:
      - Para cada día (de hace `dias` días hasta ayer):
        - num_ordenes = base * mult_dia * (1 + tendencia) * ruido
        - Cada orden: hora muestreada según mult_hora; items según popularidad
        - Descuenta stock y registra MovimientoInventario por cada item

    Limitaciones (intencionales para mantener simple):
      - No se reabastece automáticamente; si un producto se agota en algún
        día, se omite. En práctica el stock inicial es alto y se cubre.
    """
    productos_por_sucursal: dict[str, list[Producto]] = {}
    for sucursal in tenant.sucursales:
        productos_por_sucursal[sucursal.id] = (
            db.query(Producto)
              .filter_by(tenant_id=tenant.id, sucursal_id=sucursal.id, activo=True)
              .all()
        )

    # Pesos de productos según popularidad declarada en spec
    pop_por_nombre = {p[0]: p[6] for p in spec["productos"]}

    sucursales = list(tenant.sucursales)
    metodos = spec["metodos_pago"]
    items_lo, items_hi = spec["items_por_orden"]
    base_dia = spec["ordenes_base_dia"]
    demanda_dia = spec["demanda_dia"]
    demanda_hora = spec["demanda_hora"]

    # Distribución de hora: pre-calculamos pesos
    horas = list(range(24))
    pesos_hora = [max(0.001, h) for h in demanda_hora]

    hoy = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    ordenes_creadas = 0
    movimientos_creados = 0

    for d in range(dias, 0, -1):
        fecha_dia = hoy - timedelta(days=d)
        dow = fecha_dia.weekday()
        # Tendencia: día más antiguo → factor menor; ayer → factor mayor
        # Crece +0.5% por día → en 60 días total +30%
        trend = 1.0 + 0.005 * (dias - d)
        mult = demanda_dia[dow] * trend
        num_ordenes = max(0, int(round(base_dia * mult * rng.uniform(0.85, 1.15))))

        for _ in range(num_ordenes):
            # Distribuir entre sucursales (60% en 1ra, 40% en resto)
            sucursal = sucursales[0] if rng.random() < 0.6 or len(sucursales) == 1 else rng.choice(sucursales[1:])
            productos = productos_por_sucursal.get(sucursal.id, [])
            if not productos:
                continue

            # Hora muestreada
            hora = rng.choices(horas, weights=pesos_hora, k=1)[0]
            minuto = rng.randint(0, 59)
            fecha = fecha_dia.replace(hour=hora, minute=minuto, second=rng.randint(0, 59))

            # Items
            n_items = rng.randint(items_lo, items_hi)
            pesos = [pop_por_nombre.get(p.nombre, 1.0) for p in productos]
            seleccionados = rng.choices(productos, weights=pesos, k=n_items)
            # Combinar duplicados → cantidades mayores
            agg: dict[str, list] = {}
            for p in seleccionados:
                if p.id in agg:
                    agg[p.id][1] += 1
                else:
                    agg[p.id] = [p, 1]

            items_db: list[OrdenItem] = []
            stock_cambios: list[tuple[Producto, int]] = []
            subtotal = 0.0
            for prod, cantidad in agg.values():
                if (prod.stock or 0) < cantidad:
                    # No alcanza para este producto: reducimos cantidad
                    cantidad = int(prod.stock or 0)
                    if cantidad <= 0:
                        continue
                item_total = round(prod.precio * cantidad, 2)
                subtotal += item_total
                items_db.append(OrdenItem(
                    producto_id     = prod.id,
                    producto_nombre = prod.nombre,
                    cantidad        = cantidad,
                    precio_unitario = prod.precio,
                    total           = item_total,
                ))
                stock_cambios.append((prod, cantidad))

            if not items_db:
                continue  # sin stock disponible para nada

            # Domicilio (si aplica)
            domicilio = 0.0
            if rng.random() < spec["domicilio_prob"]:
                lo, hi = spec["domicilio_rango"]
                domicilio = float(rng.randint(lo // 500, hi // 500) * 500)

            metodo_pago = _ponderar(metodos)
            total = round(subtotal + domicilio, 2)

            orden = Orden(
                tenant_id   = tenant.id,
                sucursal_id = sucursal.id,
                metodo_pago = metodo_pago,
                subtotal    = round(subtotal, 2),
                domicilio   = round(domicilio, 2),
                total       = total,
                fecha       = fecha,
                items       = items_db,
            )
            db.add(orden)
            db.flush()  # para obtener orden.id

            # Descontar stock + registrar movimientos
            for prod, cantidad in stock_cambios:
                stock_antes = float(prod.stock or 0.0)
                stock_despues = round(stock_antes - cantidad, 4)
                prod.stock = stock_despues
                db.add(MovimientoInventario(
                    tenant_id     = tenant.id,
                    sucursal_id   = sucursal.id,
                    producto_id   = prod.id,
                    tipo          = "venta",
                    cantidad      = -float(cantidad),
                    stock_antes   = stock_antes,
                    stock_despues = stock_despues,
                    motivo        = None,
                    referencia_id = orden.id,
                    usuario_id    = None,
                    fecha         = fecha,
                ))
                movimientos_creados += 1

            ordenes_creadas += 1

        # Commit por día para evitar transacciones gigantes
        db.commit()

    return ordenes_creadas, movimientos_creados


# ─────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo data for Tizón POS.")
    parser.add_argument("--reset", action="store_true",
                        help="Borra los tenants demo si ya existen, antes de recrearlos.")
    parser.add_argument("--days", type=int, default=60,
                        help="Días de historia a generar (default 60).")
    parser.add_argument("--seed", type=int, default=42,
                        help="Semilla del RNG para resultados reproducibles.")
    parser.add_argument("--only", choices=["restaurante", "farmacia"], default=None,
                        help="Crear solo uno de los dos tenants demo.")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    random.seed(args.seed)  # también para _ponderar

    # Asegurar que las tablas existan
    Base.metadata.create_all(bind=engine)

    tenants_a_crear: list[dict] = []
    if args.only is None or args.only == "restaurante":
        tenants_a_crear.append(RESTAURANTE)
    if args.only is None or args.only == "farmacia":
        tenants_a_crear.append(FARMACIA)

    print("=" * 70)
    print(f" SEED DEMO - {args.days} dias - seed={args.seed}")
    print(f" DATABASE_URL: {os.environ.get('DATABASE_URL', '<sqlite local>')}")
    print("=" * 70)

    db = SessionLocal()
    try:
        for spec in tenants_a_crear:
            print(f"\n>> Tenant: {spec['nombre']} ({spec['email']})")

            existe = db.query(Tenant).filter_by(email=spec["email"]).first()
            if existe and not args.reset:
                print(f"  - Ya existe (id={existe.id}). Usa --reset para recrear. Saltando.")
                continue
            if existe and args.reset:
                _eliminar_tenant_si_existe(db, spec["email"])
                print("  - Borrado tenant previo (cascade).")

            tenant = _crear_tenant(db, spec)
            print(f"  - Creado tenant id={tenant.id}, "
                  f"sucursales={len(spec['sucursales'])}, "
                  f"productos={len(spec['productos'])}")

            n_ord, n_mov = _generar_ordenes_para_tenant(
                db, tenant, spec, dias=args.days, rng=rng
            )
            print(f"  - Generadas {n_ord} ordenes y {n_mov} movimientos en {args.days} dias.")

        print("\n" + "=" * 70)
        print(" SEED OK")
        print("=" * 70)
        print(" Login owners:")
        for spec in tenants_a_crear:
            print(f"   {spec['email']}  /  {spec['password']}")
        print()
        return 0
    except Exception as exc:
        db.rollback()
        print(f"\n[!] Error durante el seed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
