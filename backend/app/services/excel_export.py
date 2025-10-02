
import os
from typing import Dict, List
from openpyxl import Workbook

def _write_sheet(ws, rows: List[dict]):
    if not rows:
        return
    ws.append(list(rows[0].keys()))
    for r in rows:
        ws.append([r.get(k) for k in rows[0].keys()])

def export_single_to_excel(pkg: Dict, tipo: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = tipo
    data = pkg.get(tipo) if tipo in pkg else pkg.get(_map(tipo), [])
    if isinstance(data, dict):  # mayor
        ws.append(["Cuenta","Fecha","Debe","Haber","Detalle"])
        for cuenta, items in data.items():
            for it in items:
                ws.append([cuenta, it["Fecha"], it["Debe"], it["Haber"], it.get("Detalle","")])
    else:
        _write_sheet(ws, data)
    path = os.path.join(out_dir, f"{tipo}.xlsx")
    wb.save(path)
    return path

def export_all_to_excels(pkg: Dict, out_dir: str) -> List[str]:
    tipos = ["asientos","mayor","balance_ss","ee_pp","ee_rr","ee_pn","flujo","iva","ganancias","iibb","bbpp","libro_iva","sueldos"]
    paths=[]
    for t in tipos:
        paths.append(export_single_to_excel(pkg, t, out_dir))
    return paths

def _map(tipo:str)->str:
    return {
        "balance_ss":"balance_ss",
        "ee_pp":"ee_pp","ee_rr":"ee_rr","ee_pn":"ee_pn",
        "libro_iva":"libro_iva"
    }.get(tipo, tipo)
