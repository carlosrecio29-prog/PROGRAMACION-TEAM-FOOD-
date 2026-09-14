from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from backend.config import MAX_UPLOAD_BYTES
from backend.services.v2_maintenance_import_service import import_maintenance_base

app = FastAPI(title="Programación Team Food · Actualización de base")


async def read_upload(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "Solo se aceptan archivos .xlsx")
    content = await file.read()
    if not content:
        raise HTTPException(400, f"{file.filename or 'El archivo'} está vacío")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            f"{file.filename} supera {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )
    return content


@app.post("/api/v2/import-maintenance")
async def import_maintenance(
    plans: UploadFile = File(...),
    activities: UploadFile = File(...),
    monthly: UploadFile = File(...),
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    try:
        return import_maintenance_base(
            plans_content=await read_upload(plans),
            activities_content=await read_upload(activities),
            monthly_content=await read_upload(monthly),
            year=year,
            month=month,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Error actualizando la base de mantenimiento: {exc}") from exc
