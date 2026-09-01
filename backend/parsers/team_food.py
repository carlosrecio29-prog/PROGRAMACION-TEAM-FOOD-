from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.parsers.common import (
    ParsedWorkbook, as_date, as_float, cell_by_header, header_mapping,
    normalize_key, normalize_text, stable_sha256, workbook_from_bytes, normalize_turn,
)

MONTHS={"ENERO":1,"FEBRERO":2,"MARZO":3,"ABRIL":4,"MAYO":5,"JUNIO":6,"JULIO":7,"AGOSTO":8,"SEPTIEMBRE":9,"SETIEMBRE":9,"OCTUBRE":10,"NOVIEMBRE":11,"DICIEMBRE":12}
SPECIALTIES={"MEC":"MEC","MECANICA":"MEC","MECANICO":"MEC","ELE":"ELE","ELECTRICA":"ELE","ELECTRICO":"ELE","MET":"MET","METROLOGIA":"MET","SER":"SER","SERVICIO":"SER","SERVICIOS":"SER","REFRIGERACION":"SER","REFRI GERACION":"SER"}

def normalize_specialty(v): return SPECIALTIES.get(normalize_text(v),"")
def optional_float(v):
    if v in (None,""): return None
    return as_float(v,0.0)
def normalize_state(v): return normalize_text(v).rstrip(".")
def scalar_text(value):
    if value is None: return ""
    if isinstance(value,float) and value.is_integer(): return str(int(value))
    return str(value).strip()
def plan_key(group,plan): return normalize_text(f"{scalar_text(group)}-{scalar_text(plan)}")
def _sheet(wb,name):
    target=normalize_text(name)
    for ws in wb.worksheets:
        if normalize_text(ws.title)==target:return ws
    return None

def _turn_code(raw):
    code=normalize_turn(raw)
    if code.startswith("T") and code[1:].isdigit() and int(code[1:])>=10:
        return "T-"+code[1:]
    return code

def _duration_hours(text_value):
    m=re.search(r"(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2})[:.]?(\d{2})?",str(text_value or ""))
    if not m:return None
    sh,sm,eh,em=int(m.group(1)),int(m.group(2) or 0),int(m.group(3)),int(m.group(4) or 0)
    hours=((eh*60+em)-(sh*60+sm))%(24*60)/60
    return 24.0 if hours==0 else hours

def parse_team_food(content:bytes)->dict[str,ParsedWorkbook]:
    wb=workbook_from_bytes(content)
    out={k:ParsedWorkbook() for k in ("assets","plans","planning","orders","turns","technicians","roster")}

    ws=_sheet(wb,"EQUIPOS PLANTA BARRANQUILLA")
    if ws:
        m=header_mapping(ws,1); out["assets"].metadata["sheet"]=ws.title
        for n,row in enumerate(ws.iter_rows(min_row=2,values_only=True),start=2):
            code=str(cell_by_header(row,m,"Código","Codigo") or "").strip()
            if not code: continue
            crit=normalize_text(cell_by_header(row,m,"Criticidad")); crit=crit if crit in {"A","B","C"} else None
            out["assets"].rows.append({
                "excel_row":n,"code":code,"description":cell_by_header(row,m,"Descripción","Descripcion"),
                "parent_code":str(cell_by_header(row,m,"ActivoPadre") or "").strip(),
                "criticality":crit,"specialty":normalize_specialty(cell_by_header(row,m,"Especialidad")),
                "state":normalize_state(cell_by_header(row,m,"Estado")),
                "area":cell_by_header(row,m,"Departamento"),
                "line":cell_by_header(row,m,"Agrupacion","Ubicación","Ubicacion")
            })
    else: out["assets"].warnings.append("No se encontró EQUIPOS PLANTA BARRANQUILLA")

    ws=_sheet(wb,"PLAN DE TRABAJO")
    if ws:
        m=header_mapping(ws,1); out["plans"].metadata["sheet"]=ws.title
        for n,row in enumerate(ws.iter_rows(min_row=2,values_only=True),start=2):
            group=cell_by_header(row,m,"Grupo")
            plan=str(cell_by_header(row,m,"PlanTrabajo","Plan de Trabajo") or "").strip()
            spec=normalize_specialty(cell_by_header(row,m,"Especialidad"))
            if not plan or not spec: continue
            persons=optional_float(cell_by_header(row,m,"NumeroPersonas","Número de Personas"))
            execution=optional_float(cell_by_header(row,m,"TiempoEjecucion"))
            stop=optional_float(cell_by_header(row,m,"TiempoParada"))
            condition="SIN CLASIFICAR" if stop is None else ("EQUIPO DETENIDO" if stop>0 else "OPERANDO")
            out["plans"].rows.append({
                "excel_row":n,"specialty":spec,"group_code":scalar_text(group),
                "group":str(cell_by_header(row,m,"DescripcionGrupo") or group or "SIN GRUPO").strip(),
                "plan_raw":plan,"plan_key":plan_key(group,plan),
                "persons":persons if persons and persons>0 else None,
                "execution_minutes":execution if execution is None or execution>=0 else None,
                "stop_minutes":stop if stop is None or stop>=0 else None,
                "condition":condition,"state":normalize_state(cell_by_header(row,m,"Estado")),
                "order_type":normalize_text(cell_by_header(row,m,"OrdenTipo"))
            })
    else: out["plans"].warnings.append("No se encontró PLAN DE TRABAJO")

    ws=_sheet(wb,"PLANEACION")
    if ws:
        m=header_mapping(ws,1); out["planning"].metadata["sheet"]=ws.title
        for n,row in enumerate(ws.iter_rows(min_row=2,values_only=True),start=2):
            asset=str(cell_by_header(row,m,"Activo") or "").strip()
            description=str(cell_by_header(row,m,"Descripción","Descripcion") or "").strip()
            pkey=normalize_text(cell_by_header(row,m,"PlanTrabajo"))
            if not asset or not description or not pkey:continue
            out["planning"].rows.append({
                "excel_row":n,"asset_code":asset,"description":description,
                "description_key":normalize_text(description),"plan_key":pkey,
                "state":normalize_state(cell_by_header(row,m,"Estado")),
                "schedule_id":str(cell_by_header(row,m,"IdCronogramaPlaneacion") or "").strip()
            })
    else: out["planning"].warnings.append("No se encontró PLANEACION")

    ws=_sheet(wb,"ORDENES MENSUALES")
    if ws:
        m=header_mapping(ws,1); out["orders"].metadata["sheet"]=ws.title; years=[]; raw=[]
        for n,row in enumerate(ws.iter_rows(min_row=2,values_only=True),start=2):
            month=MONTHS.get(normalize_text(cell_by_header(row,m,"MES")))
            asset=str(cell_by_header(row,m,"CÓDIGO","CODIGO") or "").strip()
            obs=str(cell_by_header(row,m,"OBSERVACIÓN","OBSERVACION") or "").strip()
            spec=normalize_specialty(cell_by_header(row,m,"ESPECIALIDAD"))
            order=str(cell_by_header(row,m,"# DE ORDEN","ORDEN") or "").strip()
            try:y=int(float(cell_by_header(row,m,"AÑO","ANO")))
            except:y=None
            if y:years.append(y)
            if not month or not asset or not obs or not spec:continue
            state=normalize_state(cell_by_header(row,m,"ESTADO"))
            raw.append({
                "excel_row":n,"month":month,"asset_code":asset,
                "asset_description":cell_by_header(row,m,"DESCRIPCIÓN","DESCRIPCION"),
                "observation":obs,"observation_key":normalize_text(obs),"specialty":spec,
                "order_number":order,"state":state,
                "programmed_at":as_date(cell_by_header(row,m,"FECHA PROG")),
                "criticality":normalize_text(cell_by_header(row,m,"CRITICIDAD")),
                "area":cell_by_header(row,m,"ÁREA","AREA"),"source_year":y,
                "minutes":optional_float(cell_by_header(row,m,"TIEMPO"))
            })
        program_year=max(years) if years else datetime.now(ZoneInfo("America/Bogota")).year
        out["orders"].metadata["program_year"]=program_year

        # Conciliación contra el maestro: las filas del Excel se cuentan completas,
        # pero para programación una OT repetida representa un solo PMP.
        monthly_summary={}
        for r in raw:
            if r["state"]=="ANULADA":continue
            month_key=str(r["month"])
            spec_key=r["specialty"]
            bucket=monthly_summary.setdefault(month_key,{}).setdefault(spec_key,{
                "master_rows":0,"unique_ot":0,"pending_unique_ot":0,"finalized_unique_ot":0,
                "repeated_extra_rows":0
            })
            bucket["master_rows"]+=1

        seen_ot_by_month_spec={}
        pending_seen={}
        finalized_seen={}
        for r in raw:
            if r["state"]=="ANULADA":continue
            month_spec=(r["month"],r["specialty"])
            ot=(r["order_number"] or "").strip()
            identity=ot or f"__ROW__{r['excel_row']}"
            seen_ot_by_month_spec.setdefault(month_spec,set()).add(identity)
            if r["state"]=="PENDIENTE":pending_seen.setdefault(month_spec,set()).add(identity)
            elif r["state"]=="FINALIZADA":finalized_seen.setdefault(month_spec,set()).add(identity)

        for (month_value,specialty_value),items in seen_ot_by_month_spec.items():
            bucket=monthly_summary[str(month_value)][specialty_value]
            bucket["unique_ot"]=len(items)
            bucket["pending_unique_ot"]=len(pending_seen.get((month_value,specialty_value),set()))
            bucket["finalized_unique_ot"]=len(finalized_seen.get((month_value,specialty_value),set()))
            bucket["repeated_extra_rows"]=bucket["master_rows"]-bucket["unique_ot"]

        out["orders"].metadata["monthly_summary"]=monthly_summary

        seen=set()
        for r in raw:
            if r["state"]=="ANULADA":continue
            # Regla operativa: si el número de OT se repite en el mes, se consolida.
            # Si no hay OT, cada fila se conserva como PMP independiente.
            identity=(r["order_number"] or "").strip() or f"__ROW__{r['excel_row']}"
            sk=stable_sha256([program_year,r["month"],identity])
            if sk in seen:continue
            seen.add(sk); r["source_key"]=sk; r["program_year"]=program_year; out["orders"].rows.append(r)
    else: out["orders"].warnings.append("No se encontró ORDENES MENSUALES")

    ws=_sheet(wb,"INFORMACION DE TURNOS")
    if ws:
        out["turns"].metadata["sheet"]=ws.title
        for n,row in enumerate(ws.iter_rows(values_only=True),start=1):
            text_value=" ".join(str(v).strip() for v in row if v not in (None,""))
            if not text_value:continue
            m=re.search(r"\b(TA|T-?\d+)\b\s+",normalize_text(text_value))
            hours=_duration_hours(text_value)
            if not m or hours is None:continue
            out["turns"].rows.append({"excel_row":n,"code":_turn_code(m.group(1)),"raw_code":m.group(1),"hours":hours,"description":text_value})

    ws=_sheet(wb,"ESPECIALIDAD DE CADA TECNICO")
    if ws:
        m=header_mapping(ws,1); out["technicians"].metadata["sheet"]=ws.title
        seen=set()
        for n,row in enumerate(ws.iter_rows(min_row=2,values_only=True),start=2):
            name=str(cell_by_header(row,m,"NOMBRE","Nombre") or "").strip()
            raw_specialty=cell_by_header(row,m,"Especialiidad","Especialidad")
            if not name:continue
            specialty=normalize_specialty(raw_specialty)
            if not specialty:
                out["technicians"].warnings.append(
                    f"Fila {n} de ESPECIALIDAD DE CADA TECNICO sin especialidad reconocida: {raw_specialty}"
                )
                continue
            normalized=normalize_text(name)
            if normalized in seen:continue
            seen.add(normalized)
            out["technicians"].rows.append({
                "excel_row":n,"name":name,"name_normalized":normalized,
                "specialty":specialty,"specialty_raw":normalize_text(raw_specialty)
            })
    else: out["technicians"].warnings.append("No se encontró ESPECIALIDAD DE CADA TECNICO")

    ws=_sheet(wb,"PROGRAMACION DE TECNICOS")
    if ws:
        out["roster"].metadata["sheet"]=ws.title
        header_row=None
        for i,row in enumerate(ws.iter_rows(min_row=1,max_row=20,values_only=True),start=1):
            keys={normalize_key(v) for v in row if v not in (None,"")}
            if "ID" in keys and "NOMBRE" in keys: header_row=i;break
        if header_row:
            days=next(ws.iter_rows(min_row=header_row+1,max_row=header_row+1,values_only=True)); daycols={}
            for idx,v in enumerate(days):
                try:d=int(v)
                except:continue
                if 1<=d<=31:daycols[d]=idx
            now=datetime.now(ZoneInfo("America/Bogota")); out["roster"].metadata.update({"year":now.year,"month":now.month})
            for n,row in enumerate(ws.iter_rows(min_row=header_row+2,values_only=True),start=header_row+2):
                name=str(row[1] if len(row)>1 and row[1] is not None else "").strip()
                external=scalar_text(row[0] if row else None)
                if not name:continue
                for day,col in daycols.items():
                    if col>=len(row):continue
                    code=_turn_code(row[col])
                    if not code:continue
                    out["roster"].rows.append({
                        "excel_row":n,"external_code":external,"technician_name":name,
                        "technician_normalized":normalize_text(name),"day":day,
                        "turn_code":code,"turn_raw":normalize_text(row[col])
                    })
        known={r["code"] for r in out["turns"].rows}
        for n,row in enumerate(ws.iter_rows(values_only=True),start=1):
            for idx,value in enumerate(row[:-1]):
                raw=normalize_text(value)
                if not re.fullmatch(r"T-?\d+|TA",raw):continue
                hours=_duration_hours(row[idx+1])
                if hours is None:continue
                code=_turn_code(raw)
                if code in known:continue
                out["turns"].rows.append({"excel_row":n,"code":code,"raw_code":raw,"hours":hours,"description":str(row[idx+1] or "")})
                known.add(code)
    return out
