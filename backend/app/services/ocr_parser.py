# backend/app/services/ocr_parser.py
from typing import Dict
import logging
import re
import os


logger = logging.getLogger(__name__)

def _read_text(path: str) -> str:
    """Lee texto de PDF (si tiene texto) o de imagen (si hay Tesseract). Devuelve '' si no puede."""
    path_l = path.lower()
    text = ""

    # PDF con texto embebido
    if path_l.endswith(".pdf"):
        try:
            import pdfplumber  # requiere pdfplumber en requirements si querés usarlo
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n".join(pages)
        except Exception:
            logger.exception("No se pudo extraer texto embebido del PDF %s", path)
            text = ""

    # Imagen con OCR (opcional)
    if not text and path_l.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(path)
            # pequeño preprocesado robusto
            img = img.convert("L")
            text = pytesseract.image_to_string(img, lang="spa")
        except Exception:
            logger.exception("Error realizando OCR sobre la imagen %s", path)
            text = ""

    return text or ""


def _num(s: str) -> float:
    """Convierte '42.716,00' → 42716.00 y '7,413.52' → 7413.52 de forma robusta."""
    if not s:
        return 0.0
    s = s.strip()
    # normalizar separadores en formato AR
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def extract_fields_from_file(path: str, tipo: str) -> Dict:
    """
    Devuelve los campos mínimos para el motor contable.
    - No explota si no hay OCR: devuelve ceros y None.
    - Si hay texto, intenta extraer valores reales por regex.
    """
    text = _read_text(path)

    U = text.upper()

    # Tipo de comprobante (A/B/C) y/o literal FACTURA
    tipo_comp = None
    m_tipo = re.search(r"FACTURA\s+([ABC])", U)
    if m_tipo:
        tipo_comp = f"FACTURA {m_tipo.group(1)}"
    elif "FACTURA" in U:
        tipo_comp = "FACTURA"
    else:
        tipo_comp = (tipo or "FACTURA").upper()

    # Punto de venta y número (acepta “Nro: 0001-00012345” o variantes)
    pv = None
    nro = None
    m_pv_nro = re.search(r"(?:P\.?V\.?|PTO\.?\s*VTA\.?|PUNTO\s*DE\s*VENTA)\s*[:\-]?\s*(\d{4}).{0,4}(?:Nro\.?|Nº|N°|NUMERO|N°:)\s*[:\-]?\s*(\d{8})", U)
    if m_pv_nro:
        pv, nro = m_pv_nro.group(1), m_pv_nro.group(2)
    else:
        m_nro_simple = re.search(r"(?:Nro\.?|Nº|N°)\s*[:\-]?\s*(\d{8})", U)
        if m_nro_simple:
            nro = m_nro_simple.group(1)

    # Fecha dd/mm/aaaa
    m_fecha = re.search(r"FECHA\s*[:\s]*(\d{2}/\d{2}/\d{4})", U)
    fecha = m_fecha.group(1) if m_fecha else None

    # CUIT emisor (el primero que aparezca como “CUIT …”)
    m_cuit = re.search(r"CUIT\s*(?:NRO|Nº|N°|:)?\s*([0-9\-.]{8,13})", U)
    cuit_emisor = None
    if m_cuit:
        cuit_emisor = re.sub(r"[^0-9]", "", m_cuit.group(1))

    # TOTAL e IVA Contenido
    # Buscar primero “IVA Contenido: $ 7.413,52”
    m_iva = re.search(r"IVA\s*CONTENIDO\s*[:\s]*\$?\s*([0-9\.\,]+)", U)
    iva_contenido = _num(m_iva.group(1)) if m_iva else 0.0

    # TOTAL al pie (“TOTAL $ 42.716,00” o “TOTAL 42.716,00”)
    m_total = re.search(r"TOTAL\s*\$?\s*([0-9\.\,]+)", U)
    total = _num(m_total.group(1)) if m_total else 0.0

    # Neto estimado = total - iva (si ambos existen)
    neto = round(total - iva_contenido, 2) if total and iva_contenido else 0.0

    # CAE y Vto CAE
    m_cae = re.search(r"C\.?A\.?E\.?\s*[:\s]*([0-9]{10,20})", U)
    cae = m_cae.group(1) if m_cae else None
    m_vto = re.search(r"VENCIMIENTO\s*C\.?A\.?E\.?\s*[:\s]*(\d{2}/\d{2}/\d{4})", U)
    vto_cae = m_vto.group(1) if m_vto else None

    return {
        "tipo": tipo_comp,
        "nro_comprobante": (f"{pv}-{nro}" if pv and nro else nro),
        "fecha": fecha,  # "dd/mm/aaaa"
        "cuit_emisor": cuit_emisor,
        "cuit_receptor": None,  # si después querés, agregá búsqueda por “C.U.I.T.: …” del cliente
        "condicion_iva_emisor": None,
        "condicion_iva_receptor": None,
        "cae": cae,
        "vto_cae": vto_cae,
        "importe_neto": neto,
        "iva_21": iva_contenido,   # para MVP consideramos todo al 21
        "iva_105": 0.0,
        "importe_total": total,
        "operacion": "COMPRA",
        "texto_base": text,  # útil para debug
    }
