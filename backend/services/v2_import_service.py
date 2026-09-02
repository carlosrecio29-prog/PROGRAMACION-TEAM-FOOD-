from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.parsers.common import (
    as_datetime,
    cell_by_header,
    header_mapping,
    normalize_text,
    workbook_from_bytes,
)


SPECIALTY_MAP={
    "MEC":"MEC",
    "MECANICO":"MEC",
    "MECANICA":"MEC",
    "ELE":"ELE",
    "ELECTRICO":"ELE",
    "ELECTRICA":"ELE",
    "MET":"MET",
    "METROLOGIA":"MET",
    "SER":"SER",
    "SERVICIO":"SER",
    "SERVICIOS":"SER",
    "REFRIGERACION":"SER",
    "REFRI GERACION":"SER",
}

ABSENCE_TYPES={
    "VAC":"VACACION",
    "VA":"VACACION",
    "INC":"INCAPACIDAD",
    "IN":"INCAPACIDAD",
    "C":"COMPENSATORIO",
    "COMP":"COMPENSATORIO",
    "DE":"DESCANSO",
    "PERM":"PERMISO",
}


def _specialty(value:Any)->str|None:
    return SPECIALTY_MAP.get(normalize_text(value)) or None


def _enabled(value:Any)->bool:
    return normalize_text(value).rstrip(".")=="HABILITADO"


def _number(value:Any)->float|None:
    if value in (None,""):
        return None
    try:
        return float(value)
    except (TypeError,ValueError):
        return None


def _scalar(value:Any)->str:
    if value is None:
        return ""
    if isinstance(value,float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _first_sheet(wb):
    return wb.worksheets[0]


def _sheet_by_name(wb,name:str):
    wanted=normalize_text(name)
    for ws in wb.worksheets:
        if normalize_text(ws.title)==wanted:
            return ws
    return None


def _plan_key(group:Any,plan:Any)->str:
    return normalize_text(f"{_scalar(group)}-{_scalar(plan)}")


def _normalize_turn_code(value:Any)->str:
    code=normalize_text(value)
    if re.fullmatch(r"T-?\d+",code):
        return "T"+re.sub(r"\D","",code)
    return code


def _duration_hours(value:Any)->float|None:
    txt=str(value or "")
    m=re.search(r"(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2})[:.]?(\d{2})?",txt)
    if not m:
        return None
    sh,sm=int(m.group(1)),int(m.group(2) or 0)
    eh,em=int(m.group(3)),int(m.group(4) or 0)
    minutes=(eh*60+em)-(sh*60+sm)
    if minutes<=0:
        minutes+=24*60
    return minutes/60.0


def _parse_assets(content:bytes)->list[dict[str,Any]]:
    wb=workbook_from_bytes(content)
    ws=_first_sheet(wb)
    m=header_mapping(ws,1)
    by_code={}
    for n,row in enumerate(ws.iter_rows(min_row=2,values_only=True),start=2):
        code=_scalar(cell_by_header(row,m,"Código","Codigo"))
        if not code:
            continue
        rec={
            "codigo":code,
            "descripcion":cell_by_header(row,m,"Descripción","Descripcion"),
            "activo_padre_codigo":_scalar(cell_by_header(row,m,"ActivoPadre")) or None,
            "marca":cell_by_header(row,m,"Marca"),
            "modelo":cell_by_header(row,m,"Modelo"),
            "serie":cell_by_header(row,m,"Serie"),
            "ubicacion":cell_by_header(row,m,"Ubicación","Ubicacion"),
            "criticidad":normalize_text(cell_by_header(row,m,"Criticidad")) or None,
            "especialidad":_specialty(cell_by_header(row,m,"Especialidad")),
            "departamento":cell_by_header(row,m,"Departamento"),
            "centro_costo":_scalar(cell_by_header(row,m,"CentroCosto")) or None,
            "agrupacion":cell_by_header(row,m,"Agrupacion"),
            "grupo_analisis":cell_by_header(row,m,"GrupoAnalisis"),
            "grupo_pdt":cell_by_header(row,m,"GrupoPDT"),
            "estado":_scalar(cell_by_header(row,m,"Estado")) or None,
            "habilitado":_enabled(cell_by_header(row,m,"Estado")),
            "fila_origen":n,
        }
        key=normalize_text(code)
        previous=by_code.get(key)
        if previous is None or (rec["habilitado"] and not previous["habilitado"]):
            by_code[key]=rec
    return list(by_code.values())


def _parse_plans(content:bytes)->list[dict[str,Any]]:
    wb=workbook_from_bytes(content)
    ws=_first_sheet(wb)
    m=header_mapping(ws,1)
    rows=[]
    for n,row in enumerate(ws.iter_rows(min_row=2,values_only=True),start=2):
        group=_scalar(cell_by_header(row,m,"Grupo"))
        plan=_scalar(cell_by_header(row,m,"PlanTrabajo","Plan de Trabajo"))
        if not group or not plan:
            continue
        people=_number(cell_by_header(row,m,"NumeroPersonas","Número de Personas"))
        rows.append({
            "grupo":group,
            "descripcion_grupo":cell_by_header(row,m,"DescripcionGrupo"),
            "plan_trabajo":plan,
            "descripcion_plan_trabajo":cell_by_header(row,m,"DescripcionPlanTrabaj","DescripcionPlanTrabajo"),
            "tipo_frecuencia":cell_by_header(row,m,"TipoFrecuencia"),
            "valor_frecuencia":_number(cell_by_header(row,m,"ValorFrecuenci","ValorFrecuencia")),
            "tiempo_ejecucion_min":_number(cell_by_header(row,m,"TiempoEjecucion")),
            "numero_personas":people if people and people>0 else None,
            "tiempo_parada_min":_number(cell_by_header(row,m,"TiempoParada")),
            "especialidad":_specialty(cell_by_header(row,m,"Especialidad")) or normalize_text(cell_by_header(row,m,"Especialidad")) or None,
            "orden_tipo":normalize_text(cell_by_header(row,m,"OrdenTipo")) or None,
            "estado":_scalar(cell_by_header(row,m,"Estado")) or None,
            "habilitado":_enabled(cell_by_header(row,m,"Estado")),
            "fila_origen":n,
        })
    return rows


def _parse_planning(content:bytes)->list[dict[str,Any]]:
    wb=workbook_from_bytes(content)
    ws=_first_sheet(wb)
    m=header_mapping(ws,1)
    rows=[]
    for n,row in enumerate(ws.iter_rows(min_row=2,values_only=True),start=2):
        asset=_scalar(cell_by_header(row,m,"Activo"))
        plan_key=_scalar(cell_by_header(row,m,"PlanTrabajo"))
        schedule=_scalar(cell_by_header(row,m,"IdCronogramaPlaneacion"))
        if not asset or not plan_key or not schedule:
            continue
        rows.append({
            "id_cronograma_planeacion":schedule,
            "activo_codigo":asset,
            "plan_clave_software":plan_key,
            "descripcion":cell_by_header(row,m,"Descripción","Descripcion"),
            "prioridad":_scalar(cell_by_header(row,m,"Prioridad")) or None,
            "usuario":cell_by_header(row,m,"Usuario"),
            "fecha_inicio":as_datetime(cell_by_header(row,m,"FechaInicio")),
            "fecha_fin":as_datetime(cell_by_header(row,m,"FechaFin")),
            "autogenerar_orden":bool(cell_by_header(row,m,"AutogenerarOrden")) if cell_by_header(row,m,"AutogenerarOrden") not in (None,"") else None,
            "programacion_fija":bool(cell_by_header(row,m,"ProgramacionFija")) if cell_by_header(row,m,"ProgramacionFija") not in (None,"") else None,
            "estado":_scalar(cell_by_header(row,m,"Estado")) or None,
            "habilitado":_enabled(cell_by_header(row,m,"Estado")),
            "fila_origen":n,
        })
    return rows


def _parse_monthly(content:bytes)->list[dict[str,Any]]:
    wb=workbook_from_bytes(content)
    ws=_first_sheet(wb)
    m=header_mapping(ws,1)
    rows=[]
    for n,row in enumerate(ws.iter_rows(min_row=2,values_only=True),start=2):
        asset=_scalar(cell_by_header(row,m,"Activo"))
        plan_key=_scalar(cell_by_header(row,m,"PlanTrabajo"))
        if not asset or not plan_key:
            continue
        rows.append({
            "titulo":cell_by_header(row,m,"Título","Titulo"),
            "activo_codigo":asset,
            "especialidad":_specialty(cell_by_header(row,m,"Especialidad")) or normalize_text(cell_by_header(row,m,"Especialidad")) or None,
            "orden_tipo":normalize_text(cell_by_header(row,m,"OrdenTipo")) or None,
            "numero_ot_raw":_scalar(cell_by_header(row,m,"Orden")),
            "responsable":cell_by_header(row,m,"Responsable"),
            "plan_clave_software":plan_key,
            "cronograma_planeacion":cell_by_header(row,m,"CronogramaPlaneacion"),
            "tiempo_planeado_min":_number(cell_by_header(row,m,"TiempoPlaneado")),
            "estado":normalize_text(cell_by_header(row,m,"Estado")) or None,
            "fila_origen":n,
        })
    return rows


def _parse_technicians(content:bytes,*,year:int,month:int)->tuple[list[dict[str,Any]],list[dict[str,Any]],list[str]]:
    wb=workbook_from_bytes(content)
    warnings=[]

    spec_ws=_sheet_by_name(wb,"especialidad de cada tecnico NO")
    spec_by_name={}
    if spec_ws:
        m=header_mapping(spec_ws,1)
        for row in spec_ws.iter_rows(min_row=2,values_only=True):
            name=_scalar(cell_by_header(row,m,"NOMBRE"))
            if name:
                spec_by_name[normalize_text(name)]=_specialty(cell_by_header(row,m,"Especialiidad","Especialidad"))

    turn_ws=_sheet_by_name(wb,"informacion de turno")
    hours_by_turn={}
    if turn_ws:
        for row in turn_ws.iter_rows(values_only=True):
            text_value=" ".join(str(v).strip() for v in row if v not in (None,""))
            if not text_value:
                continue
            m=re.search(r"\b(TA|T-?\d+)\b",normalize_text(text_value))
            if not m:
                continue
            code=_normalize_turn_code(m.group(1))
            hours=_duration_hours(text_value)
            if hours is not None:
                hours_by_turn[code]=hours

    roster_ws=_sheet_by_name(wb,"programacion de tecnicos")
    if roster_ws is None:
        raise ValueError("No se encontró la hoja PROGRAMACION DE TECNICOS")

    # Fila 2 contiene los días del mes; columnas A/B son ID y nombre.
    day_row=next(roster_ws.iter_rows(min_row=2,max_row=2,values_only=True))
    day_columns={}
    for idx,value in enumerate(day_row):
        try:
            day=int(value)
        except (TypeError,ValueError):
            continue
        if 1<=day<=31:
            day_columns[idx]=day

    technicians=[]
    schedule=[]
    for n,row in enumerate(roster_ws.iter_rows(min_row=3,values_only=True),start=3):
        name=_scalar(row[1] if len(row)>1 else None)
        if not name:
            continue
        normalized=normalize_text(name)
        specialty=spec_by_name.get(normalized)
        if specialty is None:
            warnings.append(f"{name}: especialidad pendiente por definir")
        technicians.append({
            "identificacion":_scalar(row[0] if row else None) or None,
            "nombre":name,
            "nombre_normalizado":normalized,
            "especialidad":specialty,
            "fila_origen":n,
        })
        for idx,day in day_columns.items():
            raw=_scalar(row[idx] if idx<len(row) else None)
            if not raw:
                continue
            try:
                work_date=date(year,month,day)
            except ValueError:
                continue
            normalized_raw=normalize_text(raw)
            absence=ABSENCE_TYPES.get(normalized_raw)
            if absence:
                schedule.append({
                    "nombre_normalizado":normalized,
                    "fecha":work_date,
                    "turno_codigo":normalized_raw,
                    "tipo_dia":absence,
                    "horas_disponibles":0.0,
                    "fila_origen":n,
                })
                continue
            code=_normalize_turn_code(raw)
            hours=hours_by_turn.get(code)
            if hours is None:
                warnings.append(f"{name} {work_date}: turno {raw} sin horas definidas")
                hours=0.0
            schedule.append({
                "nombre_normalizado":normalized,
                "fecha":work_date,
                "turno_codigo":raw,
                "tipo_dia":"TRABAJO",
                "horas_disponibles":hours,
                "fila_origen":n,
            })

    return technicians,schedule,warnings


def import_software_base(
    *,
    assets_content:bytes,
    plans_content:bytes,
    planning_content:bytes,
    monthly_content:bytes,
    technicians_content:bytes,
    year:int,
    month:int,
)->dict[str,Any]:
    if not (1<=month<=12):
        raise ValueError("Mes inválido")

    assets=_parse_assets(assets_content)
    plans=_parse_plans(plans_content)
    planning=_parse_planning(planning_content)
    monthly=_parse_monthly(monthly_content)
    technicians,tech_schedule,tech_warnings=_parse_technicians(technicians_content,year=year,month=month)

    period=date(year,month,1)
    warnings=list(tech_warnings)

    with get_engine().begin() as conn:
        conn.execute(text("""TRUNCATE TABLE
          programacion.programacion_tecnico,
          programacion.orden_mantenimiento,
          programacion.planeacion,
          programacion.tecnico,
          programacion.plan_trabajo,
          programacion.activo
          RESTART IDENTITY CASCADE"""))

        if assets:
            conn.execute(text("""INSERT INTO programacion.activo(
              codigo,descripcion,activo_padre_codigo,marca,modelo,serie,ubicacion,criticidad,
              especialidad,departamento,centro_costo,agrupacion,grupo_analisis,grupo_pdt,
              estado,habilitado,fila_origen
            ) VALUES(
              :codigo,:descripcion,:activo_padre_codigo,:marca,:modelo,:serie,:ubicacion,:criticidad,
              :especialidad,:departamento,:centro_costo,:agrupacion,:grupo_analisis,:grupo_pdt,
              :estado,:habilitado,:fila_origen
            )"""),assets)

        if plans:
            conn.execute(text("""INSERT INTO programacion.plan_trabajo(
              grupo,descripcion_grupo,plan_trabajo,descripcion_plan_trabajo,tipo_frecuencia,
              valor_frecuencia,tiempo_ejecucion_min,numero_personas,tiempo_parada_min,
              especialidad,orden_tipo,estado,habilitado,fila_origen
            ) VALUES(
              :grupo,:descripcion_grupo,:plan_trabajo,:descripcion_plan_trabajo,:tipo_frecuencia,
              :valor_frecuencia,:tiempo_ejecucion_min,:numero_personas,:tiempo_parada_min,
              :especialidad,:orden_tipo,:estado,:habilitado,:fila_origen
            )"""),plans)

        asset_map={
            normalize_text(r["codigo"]):int(r["id"])
            for r in conn.execute(text("SELECT id,codigo FROM programacion.activo")).mappings()
        }
        plan_map={
            _plan_key(r["grupo"],r["plan_trabajo"]):int(r["id"])
            for r in conn.execute(text("SELECT id,grupo,plan_trabajo FROM programacion.plan_trabajo")).mappings()
        }

        planning_db=[]
        missing_planning_plans=0
        for r in planning:
            aid=asset_map.get(normalize_text(r["activo_codigo"]))
            if aid is None:
                warnings.append(f"Planeación fila {r['fila_origen']}: activo {r['activo_codigo']} no encontrado")
                continue
            pid=plan_map.get(normalize_text(r["plan_clave_software"]))
            if pid is None:
                missing_planning_plans+=1
            planning_db.append({
                **r,
                "activo_id":aid,
                "plan_trabajo_id":pid,
            })

        if planning_db:
            conn.execute(text("""INSERT INTO programacion.planeacion(
              id_cronograma_planeacion,activo_id,plan_trabajo_id,plan_clave_software,
              descripcion,prioridad,usuario,fecha_inicio,fecha_fin,autogenerar_orden,
              programacion_fija,estado,habilitado,fila_origen
            ) VALUES(
              :id_cronograma_planeacion,:activo_id,:plan_trabajo_id,:plan_clave_software,
              :descripcion,:prioridad,:usuario,:fecha_inicio,:fecha_fin,:autogenerar_orden,
              :programacion_fija,:estado,:habilitado,:fila_origen
            )"""),planning_db)

        planning_lookup=defaultdict(list)
        for r in conn.execute(text("""SELECT
              p.id,p.id_cronograma_planeacion,p.plan_clave_software,p.descripcion,p.habilitado,
              a.codigo activo_codigo
            FROM programacion.planeacion p
            JOIN programacion.activo a ON a.id=p.activo_id""")).mappings():
            planning_lookup[(normalize_text(r["activo_codigo"]),normalize_text(r["plan_clave_software"]))].append(dict(r))

        occurrence=Counter()
        order_db=[]
        missing_order_plans=0
        ambiguous_planning=0
        for r in monthly:
            aid=asset_map.get(normalize_text(r["activo_codigo"]))
            if aid is None:
                warnings.append(f"PMP fila {r['fila_origen']}: activo {r['activo_codigo']} no encontrado")
                continue

            pid=plan_map.get(normalize_text(r["plan_clave_software"]))
            if pid is None:
                missing_order_plans+=1

            candidates=planning_lookup.get((normalize_text(r["activo_codigo"]),normalize_text(r["plan_clave_software"])),[])
            enabled=[x for x in candidates if x["habilitado"]]
            candidates=enabled or candidates
            if r.get("cronograma_planeacion"):
                exact=[x for x in candidates if normalize_text(x.get("descripcion"))==normalize_text(r["cronograma_planeacion"])]
                if exact:
                    candidates=exact
            if len(candidates)>1:
                ambiguous_planning+=1
            planning_id=min((int(x["id"]) for x in candidates),default=None)

            ot_raw=normalize_text(r["numero_ot_raw"])
            numero_ot=None if ot_raw in {"","SIN ASIGNAR"} else _scalar(r["numero_ot_raw"])
            base_identity="|".join([
                str(period),
                numero_ot or "SIN ASIGNAR",
                normalize_text(r["activo_codigo"]),
                normalize_text(r["plan_clave_software"]),
                normalize_text(r.get("titulo")),
                normalize_text(r.get("cronograma_planeacion")),
            ])
            occurrence[base_identity]+=1
            source_key=hashlib.sha256(f"{base_identity}|{occurrence[base_identity]}".encode("utf-8")).hexdigest()
            order_db.append({
                **r,
                "source_key":source_key,
                "periodo":period,
                "numero_ot":numero_ot,
                "activo_id":aid,
                "planeacion_id":planning_id,
                "plan_trabajo_id":pid,
            })

        if order_db:
            conn.execute(text("""INSERT INTO programacion.orden_mantenimiento(
              source_key,periodo,numero_ot,activo_id,planeacion_id,plan_trabajo_id,
              plan_clave_software,titulo,especialidad,orden_tipo,responsable,
              cronograma_planeacion,tiempo_planeado_min,estado,fila_origen
            ) VALUES(
              :source_key,:periodo,:numero_ot,:activo_id,:planeacion_id,:plan_trabajo_id,
              :plan_clave_software,:titulo,:especialidad,:orden_tipo,:responsable,
              :cronograma_planeacion,:tiempo_planeado_min,:estado,:fila_origen
            )"""),order_db)

        if technicians:
            conn.execute(text("""INSERT INTO programacion.tecnico(
              identificacion,nombre,nombre_normalizado,especialidad,fila_origen
            ) VALUES(
              :identificacion,:nombre,:nombre_normalizado,:especialidad,:fila_origen
            )"""),technicians)

        technician_map={
            r["nombre_normalizado"]:int(r["id"])
            for r in conn.execute(text("SELECT id,nombre_normalizado FROM programacion.tecnico")).mappings()
        }
        schedule_db=[]
        for r in tech_schedule:
            tid=technician_map.get(r["nombre_normalizado"])
            if tid is None:
                continue
            schedule_db.append({**r,"tecnico_id":tid})

        if schedule_db:
            conn.execute(text("""INSERT INTO programacion.programacion_tecnico(
              tecnico_id,fecha,turno_codigo,tipo_dia,horas_disponibles,fila_origen
            ) VALUES(
              :tecnico_id,:fecha,:turno_codigo,:tipo_dia,:horas_disponibles,:fila_origen
            )"""),schedule_db)

        status=conn.execute(text("""SELECT
          (SELECT count(*) FROM programacion.activo) activos,
          (SELECT count(*) FROM programacion.plan_trabajo) planes,
          (SELECT count(*) FROM programacion.planeacion) planeaciones,
          (SELECT count(*) FROM programacion.orden_mantenimiento) ordenes_mes,
          (SELECT count(*) FROM programacion.tecnico) tecnicos,
          (SELECT count(*) FROM programacion.programacion_tecnico) turnos_tecnico,
          (SELECT count(*) FROM programacion.plan_trabajo WHERE numero_personas IS NULL) planes_sin_numero_personas,
          (SELECT count(*) FROM programacion.plan_trabajo WHERE requiere_parada) planes_con_parada,
          (SELECT count(*) FROM programacion.tecnico WHERE especialidad IS NULL) tecnicos_sin_especialidad,
          (SELECT count(*) FROM programacion.orden_mantenimiento WHERE numero_ot IS NULL) registros_sin_ot
        """)).mappings().one()

    return {
        "ok":True,
        "periodo":str(period),
        **dict(status),
        "planeaciones_sin_plan_maestro":missing_planning_plans,
        "ordenes_sin_plan_maestro":missing_order_plans,
        "registros_pmp_con_planeacion_ambigua":ambiguous_planning,
        "warnings":warnings[:50],
    }


def get_v2_status()->dict[str,Any]:
    with get_engine().connect() as conn:
        row=conn.execute(text("""SELECT
          (SELECT count(*) FROM programacion.activo) activos,
          (SELECT count(*) FROM programacion.plan_trabajo) planes,
          (SELECT count(*) FROM programacion.planeacion) planeaciones,
          (SELECT count(*) FROM programacion.orden_mantenimiento) ordenes,
          (SELECT count(*) FROM programacion.tecnico) tecnicos,
          (SELECT count(*) FROM programacion.programacion_tecnico) programacion_tecnicos
        """)).mappings().one()
    return {"ok":True,**dict(row)}
