from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from backend.config import MAX_UPLOAD_BYTES
from backend.services.v2_maintenance_import_service import import_maintenance_base, import_operation_master
from backend.services.v2_monthly_calendar_import import import_monthly_calendar
from backend.services.v2_advance_stops import preview_advance_stops, export_advance_excel

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


@app.post("/api/v2/import-operation-master")
async def import_operation_master_file(plans: UploadFile = File(...)):
    try:
        return import_operation_master(plans_content=await read_upload(plans))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Error cargando maestro OPERACIÓN: {exc}") from exc


@app.post("/api/v2/import-monthly-calendar")
async def import_monthly_calendar_file(
    monthly: UploadFile = File(...),
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    try:
        return import_monthly_calendar(
            monthly_content=await read_upload(monthly), year=year, month=month,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Error importando Lista de Calendario: {exc}") from exc


@app.post("/api/v2/advance-stops/preview")
async def advance_stops_preview(
    monthly: UploadFile = File(...),
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    """Temporary analysis; deliberately does not import the month into Supabase."""
    try:
        return preview_advance_stops(
            content=await read_upload(monthly), year=year, month=month,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/v2/advance-stops/export.xlsx")
async def advance_stops_excel(
    monthly: UploadFile = File(...),
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    """Reprocess the same provisional Excel, without persisting it."""
    try:
        preview = preview_advance_stops(
            content=await read_upload(monthly), year=year, month=month,
        )
        content, filename = export_advance_excel(preview)
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
