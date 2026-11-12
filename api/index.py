from __future__ import annotations

from datetime import date
import logging
import json
import os
import hmac
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import text
from pydantic import BaseModel, Field

from backend.config import MAX_UPLOAD_BYTES, database_url_diagnostics
from backend.auth import (
    COOKIE_NAME,
    SESSION_HOURS,
    admin_write_guard,
    create_admin_session,
    request_is_admin,
    revoke_admin_session,
    verify_admin_password,
)
from backend.database import get_engine
from backend.services.import_service import (
    import_master_assets, import_master_classification, import_master_personnel_turns,
    import_master_plans, import_monthly_planning, import_order_states, import_technician_roster,
)
from backend.services.query_service import get_candidates, get_capacity, get_import_history, get_master_status, get_month_reconciliation, get_month_summary
from backend.services.team_food_service import import_team_food, learn_plan
from backend.services.definition_service import (
    DefinitionError, define_plan, get_pending_definitions,
)
from backend.services.v2_import_service import import_software_base, get_v2_status
from backend.services.v2_query_service import (
    get_dashboard, get_pending_plans, save_plan_complement,
    get_technicians, save_technician_complement, get_pmp,
)
from backend.services.v2_programming_runtime import (
    V2ProgrammingError, get_week_programming, save_week_programming,
    export_weekly_excel, export_weekly_pdf,
)
from backend.services.v2_closure_service import (
    V2ClosureError, get_week_closure, close_week_from_calendar, preview_week_closure,
)
from backend.services.v2_backlog_service import get_accumulated_backlog
from backend.services.v2_backlog_bootstrap_service import bootstrap_initial_backlog
from backend.services.v2_week_tracking_service import (
    V2WeeklyTrackingError, export_week_tracking_excel,
)
from backend.services.v2_manual_tracking_service import get_week_tracking, record_week_tracking, set_manual_status
from backend.services.v2_operation_exclusion_service import get_operation_exclusions
from backend.services.v2_sheet_sync_service import (
    SheetSyncError, sync_month, sync_status, probe_sheet_source,
    finalized_outside_monthly_programming,
    queue_manual_sheet_sync, pending_sheet_sync_requests, record_agent_heartbeat,
    ensure_pending_sheet_request, complete_sheet_request, error_sheet_request,
)
from backend.services.v2_progress_service import get_progress, export_progress_pdf
from backend.services.v2_monthly_close_service import (
    V2MonthlyCloseError, get_monthly_close, close_month,
)
from backend.services.programming_service import (
    ProgrammingError, close_programming, programming_detail, programming_history, save_programming,
    export_programming_excel, export_programming_pdf, reset_test_data,
)

app=FastAPI(title="Programador de Mantenimiento API",version="1.1.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])

@app.middleware("http")
async def protect_writes(request:Request,call_next):
    return await admin_write_guard(request,call_next)

class AdminLoginRequest(BaseModel):
    password:str=Field(min_length=1,max_length=256)

@app.get("/api/auth/session")
def auth_session(request:Request):
    is_admin=request_is_admin(request)
    return {
        "role":"admin" if is_admin else "viewer",
        "can_write":is_admin,
        "session_hours":SESSION_HOURS,
    }

@app.post("/api/auth/login")
def auth_login(body:AdminLoginRequest):
    if not verify_admin_password(body.password):
        raise HTTPException(401,"Clave de administrador inválida")
    token,expires_at=create_admin_session()
    response=JSONResponse({
        "ok":True,
        "role":"admin",
        "can_write":True,
        "expires_at":expires_at.isoformat(),
    })
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_HOURS*60*60,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return response

@app.post("/api/auth/logout")
def auth_logout(request:Request):
    revoke_admin_session(request.cookies.get(COOKIE_NAME))
    response=JSONResponse({"ok":True,"role":"viewer","can_write":False})
    response.delete_cookie(key=COOKIE_NAME,path="/",samesite="strict")
    return response

async def read_upload(file:UploadFile)->bytes:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(400,"Solo se aceptan archivos .xlsx")
    content=await file.read()
    if not content:raise HTTPException(400,"El archivo está vacío")
    if len(content)>MAX_UPLOAD_BYTES:raise HTTPException(413,f"El archivo supera {MAX_UPLOAD_BYTES//(1024*1024)} MB")
    return content

def run_import(fn,filename,content,**kwargs):
    try:return fn(filename,content,**kwargs)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    except Exception as exc:raise HTTPException(500,f"Error procesando archivo: {exc}") from exc


@app.get("/api/v2/sheet-sync/status")
def sheet_sync_status(request:Request,year:int=Query(...,ge=2020,le=2100),month:int=Query(...,ge=1,le=12)):
    if not request_is_admin(request):
        raise HTTPException(403,"Solo el administrador puede consultar la sincronización.")
    try:
        return sync_status(year,month)
    except SQLAlchemyError as exc:
        raise HTTPException(503,"No se pudo consultar el historial de sincronizaciones.") from exc


@app.get("/api/v2/sheet-sync/outside-programming")
def sheet_finalized_outside_programming(
    request: Request,
    year: int = Query(..., ge=2026, le=2100),
    month: int = Query(..., ge=1, le=12),
    specialty: str = Query(..., min_length=3, max_length=3),
):
    # Read-only monthly source observations; never assign them to a weekly closure.
    if not request_is_admin(request):
        raise HTTPException(403,"Solo el administrador puede consultar OT fuera de programación.")
    try:
        return finalized_outside_monthly_programming(
            year=year, month=month, specialty=specialty,
        )
    except SheetSyncError as exc:
        raise HTTPException(422,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,"No fue posible consultar las OT fuera de programación.") from exc


@app.get("/api/v2/sheet-sync/check")
def sheet_sync_check(request: Request, year: int = Query(..., ge=2026, le=2100),
                     month: int = Query(..., ge=1, le=12)):
    # Lee Google Sheets pero NUNCA modifica Supabase, auditoría ni programación.
    if not request_is_admin(request):
        raise HTTPException(403, "Solo el administrador puede verificar la conexión.")
    try:
        return probe_sheet_source(year, month)
    except SheetSyncError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/api/v2/sheet-sync")
def sheet_sync_manual(year:int=Query(...,ge=2026,le=2100),month:int=Query(...,ge=1,le=12)):
    # Sólo administrador (middleware), sin llamar Apps Script por POST.
    # Crear solicitud en cola y esperar el próximo trigger de Apps Script.
    try:
        return queue_manual_sheet_sync(year,month)
    except SheetSyncError as exc:
        raise HTTPException(503,str(exc)) from exc


def _sheet_agent_authorized(request: Request) -> None:
    secret = os.environ.get("SHEET_SYNC_SECRET", "")
    supplied = request.headers.get("Authorization", "")
    if len(secret) < 32 or not hmac.compare_digest(supplied,f"Bearer {secret}"):
        raise HTTPException(401, "Agente de Google Apps Script no autorizado.")


@app.get("/api/v2/sheet-sync/pending")
def sheet_sync_pending(request: Request):
    # Apps Script consulta solicitudes firmadas con el token, sin datos de órdenes.
    _sheet_agent_authorized(request)
    return pending_sheet_sync_requests()


class SheetAgentHeartbeat(BaseModel):
    year: int = Field(ge=2026,le=2100)
    month: int = Field(ge=1,le=12)
    filas: int = Field(ge=1,le=15000)
    unicas: int = Field(ge=1,le=15000)
    repetidas: int = Field(default=0,ge=0,le=15000)
    operaciones: int = Field(default=0,ge=0,le=15000)
    conflictos: int = Field(default=0,ge=0,le=15000)
    porEspecialidad: dict[str,int] = Field(default_factory=dict)


@app.post("/api/v2/sheet-sync/heartbeat")
def sheet_sync_heartbeat(request: Request, body: SheetAgentHeartbeat):
    _sheet_agent_authorized(request)
    try:
        return record_agent_heartbeat(body.year,body.month,body.model_dump())
    except SheetSyncError as exc:
        raise HTTPException(422,str(exc)) from exc


class SheetSyncPushRequest(BaseModel):
    year: int = Field(ge=2026, le=2100)
    month: int = Field(ge=1, le=12)
    values: list[list[str]] = Field(min_length=2, max_length=15000)
    request_id: int | None = Field(default=None, ge=1)


@app.post("/api/v2/sheet-sync/push")
def sheet_sync_push(request: Request, body: SheetSyncPushRequest):
    # Apps Script envía los datos; Vercel no tiene que entrar en la app web de Google.
    _sheet_agent_authorized(request)
    today=datetime.now(ZoneInfo("America/Bogota")).date()
    if (body.year, body.month) != (today.year, today.month):
        raise HTTPException(422, "El agente solo puede enviar el mes actual.")
    period=date(body.year,body.month,1)
    if body.request_id is not None:
        try:
            ensure_pending_sheet_request(body.request_id,period)
        except SheetSyncError as exc:
            raise HTTPException(409,str(exc)) from exc
    try:
        result = sync_month(
            year=body.year, month=body.month,
            trigger="MANUAL" if body.request_id is not None else "CRON",
            values=body.values,
        )
        if not result.get("ok"):
            raise SheetSyncError(result.get("mensaje") or "Sincronización simultánea; se reintentará.")
        if body.request_id is not None:
            complete_sheet_request(body.request_id,period,result)
        return result
    except SheetSyncError as exc:
        if body.request_id is not None:
            error_sheet_request(body.request_id,period,str(exc))
        raise HTTPException(503,str(exc)) from exc


@app.get("/api/v2/operation-exclusions")
def v2_operation_exclusions(
    year:int=Query(...,ge=2020,le=2100),
    month:int=Query(...,ge=1,le=12),
):
    try:
        return get_operation_exclusions(year=year,month=month)
    except SQLAlchemyError as exc:
        raise HTTPException(503,"No se pudo consultar el registro de actividades excluidas") from exc


@app.get("/api/health")
def health():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "ok":True,
            "service":"programador-mantenimiento",
            "version":"1.3.0",
            "database":"connected",
            "connection":database_url_diagnostics(),
        }
    except Exception as exc:
        message=str(exc)
        if "@" in message:
            parts=message.split("@")
            message="[credenciales ocultas]@" + parts[-1]
        return JSONResponse(
            status_code=503,
            content={
                "ok":False,
                "service":"programador-mantenimiento",
                "version":"1.3.0",
                "database":"disconnected",
                "connection":database_url_diagnostics(),
                "error_type":type(exc).__name__,
                "error":message[:500],
            },
        )

@app.post("/api/imports/team-food")
async def upload_team_food(file:UploadFile=File(...),year:int|None=Query(None),month:int|None=Query(None,ge=1,le=12)):
    return run_import(import_team_food,file.filename,await read_upload(file),year=year,month=month)

@app.post("/api/v2/import-base")
async def import_v2_base(
    assets:UploadFile=File(...),
    plans:UploadFile=File(...),
    planning:UploadFile=File(...),
    monthly:UploadFile=File(...),
    technicians:UploadFile=File(...),
    year:int=Query(...,ge=2020,le=2100),
    month:int=Query(...,ge=1,le=12),
):
    try:
        return import_software_base(
            assets_content=await read_upload(assets),
            plans_content=await read_upload(plans),
            planning_content=await read_upload(planning),
            monthly_content=await read_upload(monthly),
            technicians_content=await read_upload(technicians),
            year=year,
            month=month,
        )
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500,f"Error importando base V2: {exc}") from exc

@app.get("/api/v2/status")
def v2_status():
    try:return get_v2_status()
    except Exception as exc:raise HTTPException(500,f"Error consultando base V2: {exc}") from exc

@app.get("/api/v2/dashboard")
def v2_dashboard(year:int=2026,month:int=Query(9,ge=1,le=12)):
    try:return get_dashboard(year,month)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

class MonthlyCloseRequest(BaseModel):
    closed_by:str|None=None


@app.get("/api/v2/monthly-close")
def v2_monthly_close_status(
    year:int=2026,
    month:int=Query(9,ge=1,le=12),
):
    try:
        return get_monthly_close(year,month)
    except V2MonthlyCloseError as exc:
        raise HTTPException(422,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,"No se pudo consultar el cierre mensual") from exc


@app.post("/api/v2/monthly-close")
def v2_monthly_close(
    body:MonthlyCloseRequest,
    year:int=2026,
    month:int=Query(9,ge=1,le=12),
):
    try:
        return close_month(year,month,body.closed_by)
    except V2MonthlyCloseError as exc:
        raise HTTPException(409,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,"No se pudo registrar el cierre mensual") from exc


@app.get("/api/v2/progress")
def v2_progress(year:int=2026, month:int=Query(9,ge=1,le=12)):
    try:
        return get_progress(year,month)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@app.get("/api/v2/progress/report.pdf")
def v2_progress_report_pdf(year:int=2026,month:int=Query(9,ge=1,le=12),
                           programming_id:int|None=Query(None,ge=1)):
    try:
        content,filename=export_progress_pdf(year,month,programming_id)
        return StreamingResponse(
            iter([content]),media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "private, no-store, max-age=0",
                "X-Report-Format": "gerencial-a4" if programming_id is None else "semanal",
            }
        )
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        logging.exception("Error al generar el informe PDF de mantenimiento")
        raise HTTPException(
            500,
            "No fue posible generar el PDF en el servidor "
            f"({type(exc).__name__}). Abre el enlace PDF directamente y comparte "
            "el mensaje de error para diagnosticarlo."
        ) from exc


@app.get("/api/v2/pending-plans")
def v2_pending_plans(year:int=2026,month:int=Query(9,ge=1,le=12),specialty:str|None=None):
    try:return get_pending_plans(year,month,specialty)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

class V2PlanComplement(BaseModel):
    people:float|None=Field(default=None,gt=0)
    stop_minutes:float|None=Field(default=None,ge=0)

@app.patch("/api/v2/plans/{plan_id}")
def v2_save_plan(plan_id:int,body:V2PlanComplement):
    try:return save_plan_complement(plan_id,people=body.people,stop_minutes=body.stop_minutes)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@app.get("/api/v2/technicians")
def v2_technicians(year:int=2026,month:int=Query(9,ge=1,le=12)):
    try:return get_technicians(year,month)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

class V2TechnicianComplement(BaseModel):
    specialty:str|None=None

@app.patch("/api/v2/technicians/{technician_id}")
def v2_save_technician(technician_id:int,body:V2TechnicianComplement):
    try:return save_technician_complement(technician_id,body.specialty)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@app.get("/api/v2/pmp")
def v2_pmp(
    year:int=2026,
    month:int=Query(9,ge=1,le=12),
    specialty:str|None=None,
    area:str|None=None,
    search:str|None=None,
    limit:int=Query(300,ge=1,le=1000),
):
    try:return get_pmp(year,month,specialty=specialty,area=area,search=search,limit=limit)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

class V2WeeklyProgrammingCreate(BaseModel):
    date_from:date
    date_to:date
    specialty:str
    order_ids:list[int]=Field(min_length=1)
    created_by:str|None=None

@app.get("/api/v2/programming/week")
def v2_programming_week(date_from:date,date_to:date,specialty:str):
    try:return get_week_programming(date_from=date_from,date_to=date_to,specialty=specialty)
    except V2ProgrammingError as exc:raise HTTPException(422,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,"La base V2 no tiene aplicada la migración activa de programación/backlog") from exc

@app.post("/api/v2/programming")
def v2_save_programming(body:V2WeeklyProgrammingCreate):
    try:
        return save_week_programming(
            date_from=body.date_from,date_to=body.date_to,specialty=body.specialty,
            order_ids=body.order_ids,created_by=body.created_by
        )
    except V2ProgrammingError as exc:
        raise HTTPException(422,str(exc)) from exc

@app.get("/api/v2/backlog")
def v2_backlog(
    specialty:str|None=None,area:str|None=None,state:str|None=None,search:str|None=None,
    order_id:int|None=None,age_min:int|None=Query(None,ge=0),age_max:int|None=Query(None,ge=0),
    limit:int=Query(300,ge=1,le=1000),
):
    try:
        return get_accumulated_backlog(
            specialty=specialty,area=area,state=state,search=search,order_id=order_id,
            age_min=age_min,age_max=age_max,limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,"La base V2 no tiene aplicada la migración activa de backlog") from exc

@app.post("/api/v2/backlog/bootstrap")
async def v2_bootstrap_backlog(
    file:UploadFile=File(...),
    year:int=Query(...,ge=2020,le=2100),
    month:int=Query(...,ge=1,le=12),
    moved_by:str|None=Query(None),
):
    try:
        return bootstrap_initial_backlog(
            content=await read_upload(file),
            filename=file.filename or "lista_calendario.xlsx",
            year=year,
            month=month,
            moved_by=moved_by,
        )
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,"No se pudo construir el backlog inicial") from exc

@app.get("/api/v2/programming/{programming_id}/tracking")
def v2_week_tracking(programming_id:int):
    try:
        return get_week_tracking(programming_id)
    except V2WeeklyTrackingError as exc:
        raise HTTPException(404,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,"No se pudo consultar el seguimiento semanal") from exc

@app.get("/api/v2/programming/{programming_id}/tracking/export.xlsx")
def v2_export_week_tracking(programming_id:int,area:str|None=None):
    try:
        content,filename=export_week_tracking_excel(programming_id,area=area)
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition":f'attachment; filename="{filename}"'}
        )
    except V2WeeklyTrackingError as exc:
        raise HTTPException(404,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,"No se pudo generar el Excel de seguimiento") from exc

@app.post("/api/v2/programming/{programming_id}/tracking-file")
async def v2_record_week_tracking(
    programming_id:int,
    file:UploadFile=File(...),
    recorded_by:str|None=Query(None),
):
    try:
        return record_week_tracking(
            programming_id=programming_id,
            content=await read_upload(file),
            filename=file.filename or "lista_calendario.xlsx",
            recorded_by=recorded_by,
        )
    except V2WeeklyTrackingError as exc:
        raise HTTPException(422,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,"No se pudo guardar el seguimiento semanal") from exc

class V2ManualTrackingStatus(BaseModel):
    estado: str
    comentario: str | None = Field(None, max_length=1000)
    recorded_by: str | None = Field(None, max_length=200)

@app.patch("/api/v2/programming/{programming_id}/tracking/{programacion_item_id}")
def v2_manual_tracking_status(programming_id:int, programacion_item_id:int, body:V2ManualTrackingStatus):
    try:
        return set_manual_status(programming_id, programacion_item_id, body.estado, body.comentario, body.recorded_by)
    except V2WeeklyTrackingError as exc:
        raise HTTPException(422, str(exc)) from exc
@app.get("/api/v2/programming/{programming_id}/closure")
def v2_week_closure(programming_id:int):
    try:return get_week_closure(programming_id)
    except V2ClosureError as exc:raise HTTPException(404,str(exc)) from exc

@app.post("/api/v2/programming/{programming_id}/preview-close-file")
async def v2_preview_close_week_file(
    programming_id: int,
    file: UploadFile = File(...),
):
    try:
        return preview_week_closure(
            programming_id=programming_id, content=await read_upload(file),
        )
    except V2ClosureError as exc:
        raise HTTPException(422, str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Error al consultar la programación para comparar el cierre") from exc


@app.post("/api/v2/programming/{programming_id}/close-file")
async def v2_close_week_file(
    programming_id:int,
    file:UploadFile=File(...),
    closed_by:str|None=Query(None),
    manual_resolutions:str|None=Form(None),
):
    try:
        resolutions=[]
        if manual_resolutions:
            try:
                parsed=json.loads(manual_resolutions)
            except json.JSONDecodeError as exc:
                raise V2ClosureError("Las resoluciones manuales del cierre no tienen un formato válido.") from exc
            if not isinstance(parsed,list):
                raise V2ClosureError("Las resoluciones manuales del cierre deben enviarse como una lista.")
            resolutions=parsed
        content=await read_upload(file)
        return close_week_from_calendar(
            programming_id=programming_id,
            content=content,
            filename=file.filename or "calendario.xlsx",
            closed_by=closed_by,
            manual_resolutions=resolutions,
        )
    except V2ClosureError as exc:
        raise HTTPException(422,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,"La base V2 no tiene aplicada la migración activa de cierre/backlog") from exc

@app.get("/api/v2/programming/{programming_id}/export.xlsx")
def v2_export_programming_xlsx(programming_id:int):
    try:
        content,filename=export_weekly_excel(programming_id)
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition":f'attachment; filename="{filename}"'}
        )
    except V2ProgrammingError as exc:
        raise HTTPException(404,str(exc)) from exc

@app.get("/api/v2/programming/{programming_id}/export.pdf")
def v2_export_programming_pdf(programming_id:int):
    try:
        content,filename=export_weekly_pdf(programming_id)
        return StreamingResponse(
            iter([content]),
            media_type="application/pdf",
            headers={"Content-Disposition":f'attachment; filename="{filename}"'}
        )
    except V2ProgrammingError as exc:
        raise HTTPException(404,str(exc)) from exc

@app.get("/api/master-status")
def master_status():return get_master_status()

@app.post("/api/imports/planning")
async def upload_planning(file:UploadFile=File(...)):return run_import(import_monthly_planning,file.filename,await read_upload(file))
@app.post("/api/imports/technician-roster")
async def upload_roster(file:UploadFile=File(...),year:int|None=Query(None),month:int|None=Query(None,ge=1,le=12)):
    return run_import(import_technician_roster,file.filename,await read_upload(file),year=year,month=month)
@app.post("/api/imports/order-status")
async def upload_order_status(file:UploadFile=File(...)):return run_import(import_order_states,file.filename,await read_upload(file))
@app.post("/api/imports/masters/assets")
async def upload_master_assets(file:UploadFile=File(...)):return run_import(import_master_assets,file.filename,await read_upload(file))
@app.post("/api/imports/masters/plans")
async def upload_master_plans(file:UploadFile=File(...)):return run_import(import_master_plans,file.filename,await read_upload(file))
@app.post("/api/imports/masters/classification")
async def upload_master_classification(file:UploadFile=File(...)):return run_import(import_master_classification,file.filename,await read_upload(file))
@app.post("/api/imports/masters/personnel-turns")
async def upload_master_personnel_turns(file:UploadFile=File(...)):return run_import(import_master_personnel_turns,file.filename,await read_upload(file))

@app.get("/api/capacity")
def capacity(date_from:date,date_to:date):
    try:return get_capacity(date_from,date_to)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@app.get("/api/candidates")
def candidates(specialty:str,year:int|None=None,month:int|None=Query(None,ge=1,le=12),area:str|None=None,
               criticality:str|None=None,condition:str|None=None,plan_search:str|None=None,
               origin:str|None=None,limit:int=Query(500,ge=1,le=2000)):
    try:return get_candidates(specialty=specialty,year=year,month=month,area=area,criticality=criticality,
      condition=condition,plan_search=plan_search,origin=origin,limit=limit)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@app.get("/api/month-reconciliation")
def month_reconciliation(year:int,month:int=Query(...,ge=1,le=12)):
    return get_month_reconciliation(year=year,month=month)

@app.get("/api/month-summary")
def month_summary(year:int,month:int=Query(...,ge=1,le=12)):
    return get_month_summary(year=year,month=month)

@app.get("/api/imports")
def imports(limit:int=Query(30,ge=1,le=200)):return get_import_history(limit)

class PlanDefinition(BaseModel):
    execution_minutes:float|None=Field(default=None,gt=0)
    people:float|None=Field(default=None,gt=0)
    condition:str|None=None
    updated_by:str="PRUEBA_WEB"

@app.get("/api/definitions/pending")
def pending_definitions(year:int,month:int=Query(...,ge=1,le=12),specialty:str|None=None):
    return get_pending_definitions(year=year,month=month,specialty=specialty)

@app.post("/api/definitions/plans/{plan_id}")
def save_plan_definition(plan_id:int,body:PlanDefinition):
    try:
        return define_plan(
            plan_id=plan_id,
            execution_minutes=body.execution_minutes,
            people=body.people,
            condition=body.condition,
            updated_by=body.updated_by,
        )
    except DefinitionError as exc:
        raise HTTPException(422,str(exc)) from exc

class PlanLearning(BaseModel):
    condition:str|None=None
    people:float|None=Field(default=None,gt=0)
    updated_by:str|None=None

@app.post("/api/plans/{plan_id}/learn")
def save_plan_learning(plan_id:int,body:PlanLearning):
    try:return learn_plan(plan_id=plan_id,condition=body.condition,people=body.people,updated_by=body.updated_by)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

class ProgrammingCreate(BaseModel):
    date_from:date
    date_to:date
    specialty:str
    pmp_ids:list[int]=Field(min_length=1)
    created_by:str|None=None
    reason:str|None=None

class CloseReason(BaseModel):
    program_item_id:int
    reason_code:str|None=None
    detail:str|None=None
    related_order:str|None=None

class ProgrammingClose(BaseModel):
    programming_id:int
    version_id:int
    closed_by:str|None=None
    reasons:list[CloseReason]=[]

@app.post("/api/programming")
def create_programming(body:ProgrammingCreate):
    try:return save_programming(date_from=body.date_from,date_to=body.date_to,specialty=body.specialty,
      pmp_ids=body.pmp_ids,created_by=body.created_by,reason=body.reason)
    except ProgrammingError as exc:raise HTTPException(422,str(exc)) from exc

@app.get("/api/programming/history")
def list_programming_history(limit:int=Query(50,ge=1,le=200)):return programming_history(limit)

@app.get("/api/programming/version/{version_id}")
def get_programming_version(version_id:int):return programming_detail(version_id)

@app.get("/api/programming/version/{version_id}/export.xlsx")
def export_programming_xlsx(version_id:int):
    try:
        content,filename=export_programming_excel(version_id)
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition":f'attachment; filename="{filename}"'}
        )
    except ProgrammingError as exc:
        raise HTTPException(404,str(exc)) from exc

@app.get("/api/programming/version/{version_id}/export.pdf")
def export_programming_pdf_file(version_id:int):
    try:
        content,filename=export_programming_pdf(version_id)
        return StreamingResponse(
            iter([content]),
            media_type="application/pdf",
            headers={"Content-Disposition":f'attachment; filename="{filename}"'}
        )
    except ProgrammingError as exc:
        raise HTTPException(404,str(exc)) from exc

@app.post("/api/programming/close")
def close_program(body:ProgrammingClose):
    reason_map={x.program_item_id:x.model_dump() for x in body.reasons}
    try:return close_programming(programming_id=body.programming_id,version_id=body.version_id,
      reasons=reason_map,closed_by=body.closed_by)
    except ProgrammingError as exc:raise HTTPException(422,str(exc)) from exc

class TestResetRequest(BaseModel):
    confirmation:str

@app.post("/api/testing/reset")
def reset_testing_data(body:TestResetRequest):
    if body.confirmation!="REINICIAR PRUEBAS":
        raise HTTPException(400,"Confirmación inválida")
    return reset_test_data()


