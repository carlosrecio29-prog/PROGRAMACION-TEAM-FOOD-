from __future__ import annotations

from datetime import date
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import MAX_UPLOAD_BYTES
from backend.services.import_service import (
    import_master_assets, import_master_classification, import_master_personnel_turns,
    import_master_plans, import_monthly_planning, import_order_states, import_technician_roster,
)
from backend.services.query_service import get_candidates, get_capacity, get_import_history, get_master_status
from backend.services.team_food_service import import_team_food, learn_plan
from backend.services.programming_service import (
    ProgrammingError, close_programming, programming_detail, programming_history, save_programming,
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
def health():return {"ok":True,"service":"programador-mantenimiento","version":"1.1.0"}

@app.post("/api/imports/team-food")
async def upload_team_food(file:UploadFile=File(...),year:int|None=Query(None),month:int|None=Query(None,ge=1,le=12)):
    return run_import(import_team_food,file.filename,await read_upload(file),year=year,month=month)

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

@app.get("/api/imports")
def imports(limit:int=Query(30,ge=1,le=200)):return get_import_history(limit)

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

@app.post("/api/programming/close")
def close_program(body:ProgrammingClose):
    reason_map={x.program_item_id:x.model_dump() for x in body.reasons}
    try:return close_programming(programming_id=body.programming_id,version_id=body.version_id,
      reasons=reason_map,closed_by=body.closed_by)
    except ProgrammingError as exc:raise HTTPException(422,str(exc)) from exc
