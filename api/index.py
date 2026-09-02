from __future__ import annotations

from datetime import date
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import text
from pydantic import BaseModel, Field

from backend.config import MAX_UPLOAD_BYTES, database_url_diagnostics
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
from backend.services.v2_programming_service import (
    V2ProgrammingError, get_week_programming, save_week_programming,
    export_weekly_excel, export_weekly_pdf,
)
from backend.services.programming_service import (
    ProgrammingError, close_programming, programming_detail, programming_history, save_programming,
    export_programming_excel, export_programming_pdf, reset_test_data,
)

app=FastAPI(title="Programador de Mantenimiento API",version="1.1.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])

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
        # Evitar que una excepción llegue a exponer credenciales.
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
    try:
        return get_v2_status()
    except Exception as exc:
        raise HTTPException(500,f"Error consultando base V2: {exc}") from exc


@app.get("/api/v2/dashboard")
def v2_dashboard(year:int=2026,month:int=Query(9,ge=1,le=12)):
    try:return get_dashboard(year,month)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

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
    specialty:str

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
    created_by:str|None="CARLOS ANDRÉS RECIO MUÑOZ"

@app.get("/api/v2/programming/week")
def v2_programming_week(date_from:date,date_to:date,specialty:str):
    try:return get_week_programming(date_from=date_from,date_to=date_to,specialty=specialty)
    except V2ProgrammingError as exc:raise HTTPException(422,str(exc)) from exc

@app.post("/api/v2/programming")
def v2_save_programming(body:V2WeeklyProgrammingCreate):
    try:
        return save_week_programming(
            date_from=body.date_from,date_to=body.date_to,specialty=body.specialty,
            order_ids=body.order_ids,created_by=body.created_by
        )
    except V2ProgrammingError as exc:
        raise HTTPException(422,str(exc)) from exc

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
