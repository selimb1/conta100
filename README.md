
# Conta — MVP (FastAPI + React)

## Requisitos
- Docker y Docker Compose **o** Python 3.11 + Node 20 (local)

## Levantar con Docker (recomendado)
```bash
docker compose up --build
```
- API: http://localhost:8000/docs
- Frontend: http://localhost:5173

## Levantar sin Docker
Backend:
```bash
cd backend
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Frontend:
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Flujo
1. Crear cliente (valida CUIT).
2. Subir documentos (PNG/JPG/PDF).
3. Procesar (OCR placeholder + asientos básicos + validación de cuadre).
4. Previsualizar y exportar a Excel individual o ZIP.

## Estructura
- `backend/app/services/ocr.py` → OCR (pytesseract placeholder).
- `backend/app/services/accounting.py` → Motor contable simplificado.
- `backend/app/services/excel_export.py` → Exportadores XLSX (openpyxl).
- `backend/app/services/validate.py` → Validación de CUIT.

## Notas legales (MVP)
- El motor contable y las estructuras de salida son mínimas para demo.
- Ajustar plantillas y reglas a RT 54/59 (NUA) y esquemas AFIP.

## Datos
- DB por defecto: SQLite en `backend/data/conta.db`.
- Archivos subidos: `backend/data/storage`.

## Tests (sugerido)
- Agregar pytest con pruebas de CUIT, exportación y cuadre.

## Producción
- Migrar a PostgreSQL (DATABASE_URL).
- Frontend con build estático servido detrás de Nginx.
# conta100
