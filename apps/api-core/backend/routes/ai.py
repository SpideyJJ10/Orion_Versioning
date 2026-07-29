"""
routes/ai.py — Generador de plantillas con IA usando OpenAI.

Endpoint:
  POST /api/v3/ai/generate-pos → Analiza las necesidades del usuario y configura el POS.
"""
import os
import json
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from openai import OpenAI

from backend.auth_v3 import get_current_usuario, Rol, requiere_rol
from backend.db.session import get_db
from backend.models.orm import Tenant, TenantBranding, Categoria, Producto, Sucursal

router = APIRouter(prefix="/api/v3/ai", tags=["AI Configuration"])

class GeneratePOSRequest(BaseModel):
    description: str = Field(..., description="Descripción del negocio y sus necesidades.")

# System prompt para generar el JSON esperado
SYSTEM_PROMPT = """
Eres un experto consultor de negocios y experto en configuración de sistemas POS (Point of Sale).
El usuario te dará una descripción de su negocio.
Tu tarea es devolver estrictamente un objeto JSON (y NADA MÁS que el JSON) con la siguiente estructura:

{
  "branding": {
    "nombre_comercial": "string (nombre deducido o sugerido)",
    "nicho": "string (restaurante, retail, farmacia, servicio u otro)",
    "tema": "dark o light",
    "color_primary": "string (código HEX sugerido, ej: #e25822)",
    "color_secondary": "string (código HEX sugerido)",
    "color_accent": "string (código HEX sugerido)"
  },
  "categorias": ["string"],
  "productos_sugeridos": [
    {
      "nombre": "string",
      "precio": number (precio razonable),
      "categoria": "string (debe existir en el arreglo categorias)"
    }
  ],
  "metodos_pago": ["string"]
}

No incluyas markdown (como ```json) ni texto adicional, solo un JSON crudo válido.
Asegúrate de deducir bien el nicho y proponer colores coherentes.
"""

@router.post("/generate-pos")
def generate_pos_template(
    payload: GeneratePOSRequest,
    usuario: dict = Depends(requiere_rol(Rol.OWNER)),
    db: Session = Depends(get_db)
):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="La integración de IA no está configurada (Falta OPENAI_API_KEY)."
        )

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": payload.description}
            ],
            response_format={ "type": "json_object" },
            temperature=0.7
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Respuesta vacía de OpenAI")

        data = json.loads(content)

        # 1. Update Tenant
        tenant = db.query(Tenant).filter(Tenant.id == usuario["tenant_id"]).first()
        if tenant:
            if "metodos_pago" in data:
                tenant.metodos_pago = data["metodos_pago"]
        
        # 2. Update Branding
        branding = db.query(TenantBranding).filter(TenantBranding.tenant_id == usuario["tenant_id"]).first()
        if branding and "branding" in data:
            b_data = data["branding"]
            branding.nombre_comercial = b_data.get("nombre_comercial", branding.nombre_comercial)
            branding.nicho = b_data.get("nicho", branding.nicho)
            branding.tema = b_data.get("tema", branding.tema)
            branding.color_primary = b_data.get("color_primary", branding.color_primary)
            branding.color_secondary = b_data.get("color_secondary", branding.color_secondary)
            branding.color_accent = b_data.get("color_accent", branding.color_accent)

        # Get default sucursal
        sucursal = db.query(Sucursal).filter(Sucursal.tenant_id == usuario["tenant_id"]).first()

        # 3. Insert Categories and Products
        if sucursal:
            categorias = data.get("categorias", [])
            for cat_name in categorias:
                cat_exists = db.query(Categoria).filter(
                    Categoria.tenant_id == usuario["tenant_id"],
                    Categoria.nombre == cat_name
                ).first()
                if not cat_exists:
                    db.add(Categoria(tenant_id=usuario["tenant_id"], nombre=cat_name))
            
            db.flush()

            productos = data.get("productos_sugeridos", [])
            for prod in productos:
                # Evitar duplicados por nombre
                prod_exists = db.query(Producto).filter(
                    Producto.tenant_id == usuario["tenant_id"],
                    Producto.nombre == prod["nombre"]
                ).first()
                if not prod_exists:
                    db.add(Producto(
                        tenant_id=usuario["tenant_id"],
                        sucursal_id=sucursal.id,
                        nombre=prod["nombre"],
                        precio=prod.get("precio", 0),
                        costo=0,
                        stock=100,
                        stock_minimo=10,
                        unidad_medida="unidad",
                        categoria=prod.get("categoria", "General")
                    ))
        
        db.commit()

        return {
            "message": "Template configurado exitosamente por IA.",
            "config": data
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la generación por IA: {str(e)}")
