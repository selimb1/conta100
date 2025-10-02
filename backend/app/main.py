
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Literal
from .models import init_db, SessionLocal, Client, Document, Result, Normativa
from .schemas import ClientIn, ClientOut, DocumentOut, ResultOut, ProcessRequest
from .services.ocr_parser import extract_fields_from_file
from .services.accounting import generate_entries_and_statements
from .services.excel_export import export_all_to_excels, export_single_to_excel
from .services.afip_export import export_ddjj_iva, export_ddjj_ganancias, export_ddjj_iibb, export_ddjj_bbpp
from .services.validate import validate_cuit
from .services.zip_export import make_zip
from sqlalchemy import select
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import uuid, pathlib, aiofiles

load_dotenv()
STORAGE_DIR = os.getenv("STORAGE_DIR", "./data/storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

app = FastAPI(title="Conta API", version="0.1.0")
origins = os.getenv("ALLOW_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    init_db()

# --- Clientes CRUD ---
@app.post("/clientes", response_model=ClientOut)
def create_client(payload: ClientIn):
    if not validate_cuit(payload.cuit):
        raise HTTPException(400, "CUIT inválido (dígito verificador).")
    with SessionLocal() as db:
        c = Client(name=payload.nombre.strip(),
                   cuit=payload.cuit.strip(),
                   condicion_fiscal=payload.condicion_fiscal)
        db.add(c); db.commit(); db.refresh(c)
        return ClientOut(id=c.id, nombre=c.name, cuit=c.cuit, condicion_fiscal=c.condicion_fiscal)

@app.get("/clientes", response_model=List[ClientOut])
def list_clients():
    with SessionLocal() as db:
        rows = db.execute(select(Client)).scalars().all()
        return [ClientOut(id=r.id, nombre=r.name, cuit=r.cuit, condicion_fiscal=r.condicion_fiscal) for r in rows]

@app.delete("/clientes/{client_id}")
def delete_client(client_id: int):
    with SessionLocal() as db:
        c = db.get(Client, client_id)
        if not c: raise HTTPException(404, "Cliente no encontrado")
        db.delete(c); db.commit()
        return {"ok": True}

# --- Upload documentos ---
@app.post("/documentos/upload", response_model=DocumentOut)
async def upload_document(cliente_id: int = Form(...), tipo: str = Form(...), file: UploadFile = File(...)):
    with SessionLocal() as db:
        c = db.get(Client, cliente_id)
        if not c: raise HTTPException(404, "Cliente no encontrado")
    ext = pathlib.Path(file.filename).suffix.lower()
    fname = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(STORAGE_DIR, fname)
    async with aiofiles.open(dest, "wb") as f:
        while True:
            chunk = await file.read(1024*1024)
            if not chunk: break
            await f.write(chunk)
    with SessionLocal() as db:
        d = Document(client_id=cliente_id, tipo=tipo, path=dest)
        db.add(d); db.commit(); db.refresh(d)
        return DocumentOut(id=d.id, cliente_id=d.client_id, tipo=d.tipo, ruta_archivo=d.path)

# --- Procesar documentos (OCR + contabilidad) ---
@app.post("/procesar", response_model=ResultOut)
def procesar(payload: ProcessRequest):
    with SessionLocal() as db:
        c = db.get(Client, payload.cliente_id)
        if not c: raise HTTPException(404, "Cliente no encontrado")
        docs = db.execute(select(Document).where(Document.client_id==c.id)).scalars().all()
        if not docs: raise HTTPException(400, "Sin documentos para procesar.")
        extracted = []
        for d in docs:
            try:
                extracted.append(extract_fields_from_file(d.path, d.tipo))
            except Exception as e:
                extracted.append({"_error": str(e), "path": d.path, "tipo": d.tipo})
        acc = generate_entries_and_statements(extracted, c.condicion_fiscal)
        r = Result(client_id=c.id, tipo="paquete", contenido_json=acc)
        db.add(r); db.commit(); db.refresh(r)
        return ResultOut(id=r.id, cliente_id=c.id, tipo=r.tipo, contenido_json=r.contenido_json)

@app.get("/resultados/{cliente_id}", response_model=List[ResultOut])
def resultados(cliente_id: int):
    with SessionLocal() as db:
        rows = db.execute(select(Result).where(Result.client_id==cliente_id)).scalars().all()
        return [ResultOut(id=r.id, cliente_id=r.client_id, tipo=r.tipo, contenido_json=r.contenido_json) for r in rows]

# --- Exportaciones ---
@app.get("/exportar/{tipo}")
def exportar(tipo: Literal["asientos","mayor","balance_ss","ee_pp","ee_rr","ee_pn","flujo","iva","ganancias","iibb","bbpp","libro_iva","sueldos"], cliente_id: int):
    with SessionLocal() as db:
        rows = db.execute(select(Result).where(Result.client_id==cliente_id)).scalars().all()
        if not rows: raise HTTPException(404, "Sin resultados para exportar")
        pkg = rows[-1].contenido_json
    path = export_single_to_excel(pkg, tipo, out_dir="./exports")
    return FileResponse(path, filename=os.path.basename(path), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.get("/exportar_zip")
def exportar_zip(cliente_id: int):
    with SessionLocal() as db:
        rows = db.execute(select(Result).where(Result.client_id==cliente_id)).scalars().all()
        if not rows: raise HTTPException(404, "Sin resultados")
        pkg = rows[-1].contenido_json
    files = export_all_to_excels(pkg, out_dir="./exports")
    zip_path = make_zip(files, out_path="./exports/conta_export.zip")
    return FileResponse(zip_path, filename="conta_export.zip", media_type="application/zip")

# --- Admin normativa (MVP simple) ---
class NormativaIn(BaseModel):
    tipo: str
    version: str
    contenido_json: dict

@app.post("/admin/normativa")
def upsert_normativa(n: NormativaIn):
    with SessionLocal() as db:
        existing = db.execute(select(Normativa).where(Normativa.tipo==n.tipo)).scalar_one_or_none()
        if existing:
            existing.version = n.version
            existing.contenido_json = n.contenido_json
            db.commit()
            return {"ok": True, "updated": True}
        row = Normativa(tipo=n.tipo, version=n.version, contenido_json=n.contenido_json)
        db.add(row); db.commit()
        return {"ok": True, "created": True}

# --- Exportadores AFIP (TXT) ---
@app.get("/exportar_afip/{tipo}")
def exportar_afip(tipo: str, cliente_id: int):
    """
    Genera archivos TXT con estructura AFIP para DDJJ y libros.
    """
    from sqlalchemy import select
    from fastapi.responses import FileResponse
    with SessionLocal() as db:
        rows = db.execute(select(Result).where(Result.client_id==cliente_id)).scalars().all()
        if not rows:
            raise HTTPException(404, "Sin resultados para exportar")
        pkg = rows[-1].contenido_json

    if tipo == "iva":
        path = export_ddjj_iva(pkg["ddjj_iva"])
    elif tipo == "ganancias":
        path = export_ddjj_ganancias(pkg["ddjj_ganancias"])
    elif tipo == "iibb":
        path = export_ddjj_iibb(pkg["ddjj_iibb"])
    elif tipo == "bbpp":
        path = export_ddjj_bbpp(pkg["ddjj_bbpp"])
    else:
        raise HTTPException(400, "Tipo no reconocido")

    return FileResponse(path, filename=os.path.basename(path), media_type="text/plain")
