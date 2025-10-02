
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ClientIn(BaseModel):
    nombre: str
    cuit: str
    condicion_fiscal: str  # "Monotributista" | "Responsable Inscripto"

class ClientOut(ClientIn):
    id: int

class DocumentOut(BaseModel):
    id: int
    cliente_id: int
    tipo: str
    ruta_archivo: str

class ProcessRequest(BaseModel):
    cliente_id: int

class ResultOut(BaseModel):
    id: int
    cliente_id: int
    tipo: str
    contenido_json: dict
