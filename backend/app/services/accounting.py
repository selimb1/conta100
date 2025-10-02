from typing import List, Dict
from datetime import datetime

# ======================================================
# ============ MOTOR CONTABLE + IMPOSITIVO =============
# ======================================================

def generate_entries_and_statements(extracted_docs: List[Dict], condicion_fiscal: str) -> Dict:
    """
    Motor contable + fiscal argentino:
    - Genera asientos contables.
    - Arma libros IVA compras y ventas.
    - Calcula EECC básicos.
    - Determina DDJJ de IVA, Ganancias, IIBB y Bienes Personales.
    """

    asientos = []
    libro_iva_compras = []
    libro_iva_ventas = []
    gastos_deducibles = []  # para Ganancias
    activos = []  # para Bienes Personales

    for doc in extracted_docs:
        tipo = (doc.get("tipo") or "").upper()
        total = doc.get("importe_total") or 0.0
        neto = doc.get("importe_neto") or 0.0
        iva21 = doc.get("iva_21") or 0.0
        iva105 = doc.get("iva_105") or 0.0
        fecha = _parse_fecha(doc.get("fecha"))
        cuit_emisor = doc.get("cuit_emisor")
        cuit_receptor = doc.get("cuit_receptor")
        operacion = doc.get("operacion") or "COMPRA"

        # ============= ASIENTOS =============
        if operacion == "COMPRA":
            # IVA crédito fiscal
            asientos.append(_asiento(fecha, "Compras", neto, 0, f"CUIT {cuit_emisor}"))
            if iva21 or iva105:
                asientos.append(_asiento(fecha, "IVA Crédito Fiscal", iva21 + iva105, 0, f"CUIT {cuit_emisor}"))
            asientos.append(_asiento(fecha, "Proveedores", 0, total, f"CUIT {cuit_emisor}"))

            libro_iva_compras.append({
                "Fecha": fecha,
                "CUIT Proveedor": cuit_emisor,
                "Tipo": tipo,
                "Neto Gravado": neto,
                "IVA 21%": iva21,
                "IVA 10.5%": iva105,
                "Total": total
            })

            gastos_deducibles.append({"Fecha": fecha, "CUIT": cuit_emisor, "Importe": neto, "Tipo": tipo})

        elif operacion == "VENTA":
            # IVA débito fiscal
            asientos.append(_asiento(fecha, "Clientes", total, 0, f"CUIT {cuit_receptor}"))
            asientos.append(_asiento(fecha, "Ventas", 0, neto, f"CUIT {cuit_receptor}"))
            if iva21 or iva105:
                asientos.append(_asiento(fecha, "IVA Débito Fiscal", 0, iva21 + iva105, f"CUIT {cuit_receptor}"))

            libro_iva_ventas.append({
                "Fecha": fecha,
                "CUIT Cliente": cuit_receptor,
                "Tipo": tipo,
                "Neto Gravado": neto,
                "IVA 21%": iva21,
                "IVA 10.5%": iva105,
                "Total": total
            })

        # Detectar bienes registrables o inventarios para BBPP
        if "vehículo" in (doc.get("texto_base") or "").lower() or "inmueble" in (doc.get("texto_base") or "").lower():
            activos.append({"Fecha": fecha, "Descripción": tipo, "Valor": total})
        if "activo" in (doc.get("texto_base") or "").lower():
            activos.append({"Fecha": fecha, "Descripción": tipo, "Valor": total})

    # ============= SUMAS Y SALDOS =============
    balance_ss = _balance_sumas_y_saldos(asientos)

    # ============= EECC =============
    ee_rr = _estado_resultados(asientos)
    ee_pp = _estado_situacion_patrimonial(asientos)
    ee_pn = _estado_patrimonio_neto(ee_rr)

    # ============= DDJJ IMPOSITIVAS =============
    ddjj_iva = _ddjj_iva(libro_iva_compras, libro_iva_ventas)
    ddjj_ganancias = _ddjj_ganancias(asientos, gastos_deducibles)
    ddjj_iibb = _ddjj_iibb(libro_iva_ventas, condicion_fiscal)
    ddjj_bbpp = _ddjj_bbpp(activos)

    # ============= VALIDACIONES =============
    cuadre = round(sum(a["Debe"] for a in asientos), 2) == round(sum(a["Haber"] for a in asientos), 2)

    return {
        "asientos": asientos,
        "balance_ss": balance_ss,
        "ee_rr": ee_rr,
        "ee_pp": ee_pp,
        "ee_pn": ee_pn,
        "libro_iva_compras": libro_iva_compras,
        "libro_iva_ventas": libro_iva_ventas,
        "ddjj_iva": ddjj_iva,
        "ddjj_ganancias": ddjj_ganancias,
        "ddjj_iibb": ddjj_iibb,
        "ddjj_bbpp": ddjj_bbpp,
        "_validaciones": {"cuadre_sumas": cuadre}
    }


# =======================================================
# =============== FUNCIONES AUXILIARES ==================
# =======================================================

def _asiento(fecha, cuenta, debe, haber, detalle):
    return {"Fecha": fecha, "Cuenta": cuenta, "Debe": round(debe, 2), "Haber": round(haber, 2), "Detalle": detalle}


def _parse_fecha(s):
    if not s:
        return datetime.today().strftime("%d/%m/%Y")
    try:
        d = datetime.strptime(s, "%d/%m/%Y")
        return d.strftime("%d/%m/%Y")
    except Exception:
        return datetime.today().strftime("%d/%m/%Y")


def _balance_sumas_y_saldos(asientos):
    balance = {}
    for a in asientos:
        cta = a["Cuenta"]
        balance.setdefault(cta, {"Debe": 0.0, "Haber": 0.0})
        balance[cta]["Debe"] += a["Debe"]
        balance[cta]["Haber"] += a["Haber"]
    return [{"Cuenta": cta, "Debe": v["Debe"], "Haber": v["Haber"]} for cta, v in balance.items()]


def _estado_resultados(asientos):
    ingresos = sum(a["Haber"] for a in asientos if "Venta" in a["Cuenta"])
    costos = sum(a["Debe"] for a in asientos if "Compra" in a["Cuenta"])
    resultado = ingresos - costos
    return [
        {"Concepto": "Ventas", "Importe": ingresos},
        {"Concepto": "Costo de Ventas", "Importe": costos},
        {"Concepto": "Resultado del Ejercicio", "Importe": resultado}
    ]


def _estado_situacion_patrimonial(asientos):
    activos = sum(a["Debe"] for a in asientos if a["Cuenta"] in ["Clientes", "Caja", "Bancos"])
    pasivos = sum(a["Haber"] for a in asientos if a["Cuenta"] == "Proveedores")
    return [
        {"Activo": "Caja y Bancos", "Importe": activos},
        {"Pasivo": "Proveedores", "Importe": pasivos},
        {"Patrimonio Neto": activos - pasivos}
    ]


def _estado_patrimonio_neto(ee_rr):
    resultado = ee_rr[-1]["Importe"]
    return [{"Concepto": "Capital", "Importe": 0.0}, {"Concepto": "Resultado del Ejercicio", "Importe": resultado}]


# =======================================================
# ============= DDJJ IVA / GANANCIAS =====================
# =======================================================

def _ddjj_iva(compras, ventas):
    iva_cf = sum(c["IVA 21%"] + c["IVA 10.5%"] for c in compras)
    iva_df = sum(v["IVA 21%"] + v["IVA 10.5%"] for v in ventas)
    saldo = iva_df - iva_cf
    return [{
        "Periodo": datetime.today().strftime("%m/%Y"),
        "IVA Crédito Fiscal": iva_cf,
        "IVA Débito Fiscal": iva_df,
        "Saldo a Ingresar": saldo
    }]


def _ddjj_ganancias(asientos, gastos_deducibles):
    ingresos = sum(a["Haber"] for a in asientos if "Venta" in a["Cuenta"])
    costos = sum(a["Debe"] for a in asientos if "Compra" in a["Cuenta"])
    gastos = sum(g["Importe"] for g in gastos_deducibles)
    ganancia_neta = ingresos - (costos + gastos)

    if ganancia_neta <= 500000:
        impuesto = ganancia_neta * 0.25
    elif ganancia_neta <= 5000000:
        impuesto = ganancia_neta * 0.30
    else:
        impuesto = ganancia_neta * 0.35

    anticipos = round(impuesto / 5, 2)

    return [{
        "Periodo Fiscal": datetime.today().year,
        "Ingresos Gravados": ingresos,
        "Costos": costos,
        "Gastos Deducibles": gastos,
        "Ganancia Neta Imponible": ganancia_neta,
        "Impuesto Determinado": impuesto,
        "Anticipos Estimados": anticipos
    }]


# =======================================================
# ============= DDJJ IIBB (Ingresos Brutos) ==============
# =======================================================

def _ddjj_iibb(libro_iva_ventas, condicion_fiscal: str):
    """
    Determina la base imponible de IIBB según ventas gravadas.
    Toma 3,5 % general, o 1,75 % si es servicios profesionales.
    """
    total_ventas = sum(v["Neto Gravado"] for v in libro_iva_ventas)
    if "profesional" in condicion_fiscal.lower():
        alicuota = 0.0175
    else:
        alicuota = 0.035
    impuesto = total_ventas * alicuota
    return [{
        "Jurisdicción": "Tucumán",
        "Base Imponible": total_ventas,
        "Alicuota (%)": alicuota * 100,
        "Impuesto Determinado": round(impuesto, 2)
    }]


# =======================================================
# ========== DDJJ BIENES PERSONALES (BBPP) ==============
# =======================================================

def _ddjj_bbpp(activos):
    """
    Evalúa bienes declarables (vehículos, inmuebles, activos registrados)
    aplicando 0,5 % sobre el valor total.
    """
    total_activos = sum(a["Valor"] for a in activos)
    impuesto = total_activos * 0.005  # 0.5 %
    return [{
        "Periodo Fiscal": datetime.today().year,
        "Total Bienes Gravados": total_activos,
        "Alicuota (%)": 0.5,
        "Impuesto Determinado": round(impuesto, 2)
    }]
