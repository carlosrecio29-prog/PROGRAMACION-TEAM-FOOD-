from __future__ import annotations
from datetime import date
from typing import Any
from sqlalchemy import text
from backend.database import get_engine

def get_capacity(date_from: date, date_to: date) -> dict[str, Any]:
    if date_to < date_from or (date_to-date_from).days > 6: raise ValueError("El rango debe ser de 1 a 7 días")
    with get_engine().connect() as conn:
        rows=conn.execute(text("""SELECT e.codigo AS especialidad,COALESCE(SUM(tu.horas_disponibles),0)::float AS hh_disponibles
        FROM mantenimiento.especialidad e LEFT JOIN mantenimiento.tecnico t ON t.especialidad_id=e.id AND t.activo=TRUE
        LEFT JOIN mantenimiento.programacion_tecnico pt ON pt.tecnico_id=t.id AND pt.fecha BETWEEN :desde AND :hasta
        LEFT JOIN mantenimiento.turno tu ON tu.id=pt.turno_id WHERE e.codigo IN ('MEC','ELE','MET','SER')
        GROUP BY e.codigo ORDER BY e.codigo"""),{"desde":date_from,"hasta":date_to}).mappings().all()
    return {r["especialidad"]:{"available":float(r["hh_disponibles"] or 0),"target":float(r["hh_disponibles"] or 0)*.8,"standby":float(r["hh_disponibles"] or 0)*.2} for r in rows}

def get_candidates(*,specialty:str,year:int|None=None,month:int|None=None,area:str|None=None,criticality:str|None=None,
                   condition:str|None=None,plan_search:str|None=None,origin:str|None=None,limit:int=500):
    origin=(origin or "ALL").upper()
    if origin not in {"ALL","MES","BACKLOG"}: raise ValueError("Origen inválido")
    filters=["v.especialidad=:especialidad","v.estado_orden <> 'FINALIZADA'"];params={"especialidad":specialty.upper(),"limit":limit}
    if year is not None:filters.append("v.anio=:anio");params["anio"]=year
    if month is not None:filters.append("v.mes=:mes");params["mes"]=month
    if year is None and month is None:
        filters.append("(b.pmp_id is not null or (v.anio,v.mes)=(select pm.anio,pm.mes from mantenimiento.periodo_mensual pm order by pm.anio desc,pm.mes desc limit 1))")
    if area:filters.append("LOWER(COALESCE(v.area_nombre,''))=LOWER(:area)");params["area"]=area
    if criticality:filters.append("v.criticidad=:criticidad");params["criticidad"]=criticality.upper()
    if condition:filters.append("v.condicion=:condicion");params["condicion"]=condition.upper()
    if plan_search:filters.append("LOWER(v.plan_trabajo) LIKE LOWER(:plan_search)");params["plan_search"]=f"%{plan_search}%"
    used="""not exists(select 1 from mantenimiento.programacion_item ux
      join mantenimiento.programacion_version uv on uv.id=ux.programacion_version_id and uv.es_actual=true
      where ux.pmp_id=v.pmp_id)"""
    if origin=="MES":filters.extend(["b.pmp_id is null",used])
    elif origin=="BACKLOG":filters.append("b.pmp_id is not null")
    else:filters.append(f"(b.pmp_id is not null or {used})")
    sql=f"""SELECT v.*,CASE WHEN b.pmp_id IS NOT NULL THEN 'BACKLOG' ELSE 'MES' END AS origen
    FROM mantenimiento.vw_pmp_calculado v LEFT JOIN mantenimiento.vw_backlog b ON b.pmp_id=v.pmp_id
    WHERE {' AND '.join(filters)}
    ORDER BY CASE WHEN b.pmp_id IS NOT NULL THEN 0 ELSE 1 END,
      CASE v.criticidad WHEN 'A' THEN 1 WHEN 'B' THEN 2 WHEN 'C' THEN 3 ELSE 4 END,
      v.area_nombre,v.grupo_plan,v.plan_trabajo,v.activo_codigo LIMIT :limit"""
    with get_engine().connect() as conn:return [dict(r) for r in conn.execute(text(sql),params).mappings().all()]

def get_import_history(limit:int=30):
    with get_engine().connect() as conn:
        return [dict(r) for r in conn.execute(text("""SELECT id,tipo,nombre_archivo,fecha_importacion,estado,
        filas_leidas,filas_insertadas,filas_actualizadas,filas_rechazadas,mensaje
        FROM mantenimiento.importacion ORDER BY fecha_importacion DESC LIMIT :limit"""),{"limit":limit}).mappings().all()]

def get_master_status():
    with get_engine().connect() as conn:
        period=conn.execute(text("SELECT anio,mes FROM mantenimiento.periodo_mensual ORDER BY anio DESC,mes DESC LIMIT 1")).mappings().one_or_none()
        counts=conn.execute(text("""SELECT
          (SELECT count(*) FROM mantenimiento.activo WHERE activo=true) activos,
          (SELECT count(*) FROM mantenimiento.plan_trabajo WHERE activo=true) planes,
          (SELECT count(*) FROM mantenimiento.actividad_maestra WHERE activo=true) actividades,
          (SELECT count(*) FROM mantenimiento.plan_trabajo p LEFT JOIN mantenimiento.clasificacion_plan cp ON cp.plan_trabajo_id=p.id
            WHERE p.activo=true AND COALESCE(cp.personas_usar,p.personas_defecto) IS NULL) planes_sin_personas,
          (SELECT count(*) FROM mantenimiento.plan_trabajo p LEFT JOIN mantenimiento.clasificacion_plan cp ON cp.plan_trabajo_id=p.id
            WHERE p.activo=true AND COALESCE(cp.condicion,'SIN CLASIFICAR')='SIN CLASIFICAR') planes_sin_condicion""")).mappings().one()
        last=conn.execute(text("""SELECT estado,anio,mes,filas_leidas,filas_procesadas,mensaje,iniciado_en,finalizado_en
          FROM mantenimiento.sincronizacion_fuente_maestra ORDER BY iniciado_en DESC LIMIT 1""")).mappings().one_or_none()
    return {"latest_period":dict(period) if period else None,"counts":dict(counts),"last_sync":dict(last) if last else None}
