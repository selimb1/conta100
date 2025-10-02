import os
from datetime import datetime

BASE_PATH = "./exports/afip"

def ensure_dir():
    os.makedirs(BASE_PATH, exist_ok=True)

# ===================================================
# =============== EXPORTADORES AFIP =================
# ===================================================

def export_ddjj_iva(ddjj_iva: dict):
    """
    Genera TXT compatible con Libro IVA Digital / F.2002
    Campos: Periodo;IVA_CF;IVA_DF;Saldo
    """
    ensure_dir()
    fpath = os.path.join(BASE_PATH, f"ddjj_iva_{datetime.today().strftime('%Y%m')}.txt")
    with open(fpath, "w", encoding="utf-8") as f:
        for r in ddjj_iva:
            linea = f"{r['Periodo']};{r['IVA Crédito Fiscal']:.2f};{r['IVA Débito Fiscal']:.2f};{r['Saldo a Ingresar']:.2f}\n"
            f.write(linea)
    return fpath


def export_ddjj_ganancias(ddjj_ganancias: dict):
    """
    Genera TXT simplificado para F.713 (Ganancias)
    Campos: Periodo;Ingresos;Costos;Gastos;Ganancia;Impuesto;Anticipos
    """
    ensure_dir()
    fpath = os.path.join(BASE_PATH, f"ddjj_ganancias_{datetime.today().year}.txt")
    with open(fpath, "w", encoding="utf-8") as f:
        for r in ddjj_ganancias:
            linea = f"{r['Periodo Fiscal']};{r['Ingresos Gravados']:.2f};{r['Costos']:.2f};{r['Gastos Deducibles']:.2f};{r['Ganancia Neta Imponible']:.2f};{r['Impuesto Determinado']:.2f};{r['Anticipos Estimados']:.2f}\n"
            f.write(linea)
    return fpath


def export_ddjj_iibb(ddjj_iibb: dict):
    """
    TXT compatible con SIFERE Local (jurisdicción Tucumán)
    Campos: Jurisdiccion;Base;Alicuota;Impuesto
    """
    ensure_dir()
    fpath = os.path.join(BASE_PATH, f"ddjj_iibb_{datetime.today().strftime('%Y%m')}.txt")
    with open(fpath, "w", encoding="utf-8") as f:
        for r in ddjj_iibb:
            linea = f"{r['Jurisdicción']};{r['Base Imponible']:.2f};{r['Alicuota (%)']:.2f};{r['Impuesto Determinado']:.2f}\n"
            f.write(linea)
    return fpath


def export_ddjj_bbpp(ddjj_bbpp: dict):
    """
    TXT base para F.762 (Bienes Personales)
    Campos: Periodo;TotalBienes;Alicuota;Impuesto
    """
    ensure_dir()
    fpath = os.path.join(BASE_PATH, f"ddjj_bbpp_{datetime.today().year}.txt")
    with open(fpath, "w", encoding="utf-8") as f:
        for r in ddjj_bbpp:
            linea = f"{r['Periodo Fiscal']};{r['Total Bienes Gravados']:.2f};{r['Alicuota (%)']:.2f};{r['Impuesto Determinado']:.2f}\n"
            f.write(linea)
    return fpath
