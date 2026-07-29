"""
OCR de facturas de proveedor (MVP).

Pipeline:
  1) Pre-proceso (PIL: grayscale, autocontrast)
  2) Tesseract → texto crudo
  3) Parser regex → líneas estructuradas
  4) Match difuso contra catálogo del tenant

Para producir, instala:
    pip install pytesseract Pillow
    + binario `tesseract` en el sistema (apt-get install tesseract-ocr tesseract-ocr-spa)

Documentación: docs/AI_MODULES.md sección 2
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, asdict
from difflib import get_close_matches
from typing import List, Optional

# Dependencias opcionales: el web service no las requiere para arrancar.
try:
    import pytesseract
    from PIL import Image, ImageOps
    TESSERACT_OK = True
except ImportError:  # pragma: no cover
    TESSERACT_OK = False


@dataclass
class LineaFactura:
    descripcion: str
    cantidad: float
    precio_unitario: Optional[float]
    total: Optional[float]
    sku_sugerido: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# Patrones tolerantes a variaciones reales:
#   "2 x Coca Cola 350ml  $1,500  $3,000"
#   "3X PAN BLANCO        2.500"
LINE_PATTERN = re.compile(
    r"^\s*(?P<cant>\d+(?:[.,]\d+)?)\s*[xX]\s*"
    r"(?P<desc>.+?)\s+"
    r"\$?\s*(?P<precio>[\d.,]+)"
    r"(?:\s+\$?\s*(?P<total>[\d.,]+))?\s*$"
)


def _to_float(s: Optional[str]) -> Optional[float]:
    """Convierte '1.500,00' o '1,500.00' o '1500' a float."""
    if not s:
        return None
    cleaned = s.replace(" ", "")
    # Heurística: si tiene coma y punto, asumimos punto = miles, coma = decimal.
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def preprocesar_imagen(raw: bytes):
    """Mejora la legibilidad antes de pasar a Tesseract."""
    if not TESSERACT_OK:
        raise RuntimeError(
            "Pillow/pytesseract no instalados. Agrega a requirements-ml.txt: "
            "pytesseract>=0.3.10, Pillow>=10.0.0"
        )
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return img


def extraer_texto(raw: bytes, lang: str = "spa") -> str:
    """Devuelve el texto crudo extraído por Tesseract."""
    img = preprocesar_imagen(raw)
    return pytesseract.image_to_string(img, lang=lang)


def parsear_lineas(texto: str) -> List[LineaFactura]:
    """Aplica regex línea por línea y descarta lo que no parezca un ítem."""
    lineas: List[LineaFactura] = []
    for raw in texto.splitlines():
        m = LINE_PATTERN.match(raw)
        if not m:
            continue
        cant   = _to_float(m.group("cant")) or 0
        precio = _to_float(m.group("precio"))
        total  = _to_float(m.group("total"))
        if cant <= 0 or precio is None:
            continue
        lineas.append(LineaFactura(
            descripcion     = m.group("desc").strip().title()[:120],
            cantidad        = cant,
            precio_unitario = precio,
            total           = total if total is not None else cant * precio,
        ))
    return lineas


def match_catalogo(
    lineas: List[LineaFactura],
    catalogo: list[dict],
    cutoff: float = 0.6,
) -> List[LineaFactura]:
    """Match difuso por nombre. catalogo: [{id, nombre, sku}]."""
    if not catalogo:
        return lineas
    nombres = [p["nombre"].lower() for p in catalogo]
    for ln in lineas:
        cand = get_close_matches(ln.descripcion.lower(), nombres, n=1, cutoff=cutoff)
        if cand:
            idx = nombres.index(cand[0])
            ln.sku_sugerido = catalogo[idx].get("sku")
    return lineas


def procesar_factura(raw: bytes, catalogo: list[dict] | None = None) -> dict:
    """Pipeline completo. Útil para tests y para el endpoint."""
    texto  = extraer_texto(raw)
    lineas = parsear_lineas(texto)
    if catalogo:
        lineas = match_catalogo(lineas, catalogo)
    return {
        "texto_crudo": texto,
        "lineas":      [ln.to_dict() for ln in lineas],
        "total_lineas": len(lineas),
    }
