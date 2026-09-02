from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text

from backend.database import get_engine


VALID_SPECIALTIES={"MEC","ELE","MET","SER"}


def _period(year:int,month:int)->date:
    if year<2020 or year>2100 or month<1 or month>12:
        raise ValueError("Periodo inválido")
    return date(year,month,1)


def get_dashboard(year:int,month:int)->dict[str,Any]:
    period=_period(year,month)
    with get_engine().connect() as conn:
        summary=conn.execute(text("""
            WITH month_orders AS (
              SELECT o.*,p.numero_personas_efectivo,p.tiempo_parada_efectivo_min,
                     p.tiempo_ejecucion_min,p.requiere_parada
              FROM programacion.orden_mantenimiento o
              LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              WHERE o.periodo=:period
            )
            SELECT
              (SELECT count(*) FROM programacion.activo) AS activos,
              (SELECT count(*) FROM programacion.plan_trabajo) AS planes,
              (SELECT count(*) FROM programacion.planeacion) AS planeaciones,
              count(*) AS registros_pmp,
              count(DISTINCT numero_ot) FILTER (WHERE numero_ot IS NOT NULL) AS ot_distintas,
              count(*) FILTER (WHERE numero_ot IS NULL) AS registros_sin_ot,
              count(*) FILTER (WHERE plan_trabajo_id IS NULL) AS registros_sin_plan_maestro,
              count(*) FILTER (
                WHERE plan_trabajo_id IS NOT NULL
                  AND numero_personas_efectivo IS NOT NULL
                  AND tiempo_parada_efectivo_min IS NOT NULL
                  AND COALESCE(tiempo_planeado_min,tiempo_ejecucion_min) IS NOT NULL
              ) AS registros_listos,
              count(*) FILTER (
                WHERE plan_trabajo_id IS NOT NULL
                  AND numero_personas_efectivo IS NULL
              ) AS registros_sin_personas,
              count(*) FILTER (
                WHERE plan_trabajo_id IS NOT NULL
                  AND tiempo_parada_efectivo_min IS NULL
              ) AS registros_sin_tiempo_parada,
              round(COALESCE(sum(
                COALESCE(tiempo_planeado_min,tiempo_ejecucion_min)
                / 60.0 * numero_personas_efectivo
              ) FILTER (
                WHERE plan_trabajo_id IS NOT NULL
                  AND numero_personas_efectivo IS NOT NULL
                  AND COALESCE(tiempo_planeado_min,tiempo_ejecucion_min) IS NOT NULL
              ),0),2) AS hh_calculables,
              (SELECT count(*) FROM programacion.tecnico) AS tecnicos,
              (SELECT count(*) FROM programacion.tecnico WHERE especialidad_efectiva IS NULL) AS tecnicos_sin_especialidad,
              (SELECT round(COALESCE(sum(horas_disponibles),0),2)
                 FROM programacion.programacion_tecnico
                WHERE date_trunc('month',fecha)::date=:period) AS hh_tecnicos_mes
            FROM month_orders
        """),{"period":period}).mappings().one()

        pending=conn.execute(text("""
            SELECT
              count(DISTINCT p.id) FILTER (WHERE p.numero_personas_efectivo IS NULL) AS planes_sin_personas,
              count(DISTINCT p.id) FILTER (WHERE p.tiempo_parada_efectivo_min IS NULL) AS planes_sin_tiempo_parada,
              count(DISTINCT p.id) FILTER (
                WHERE p.numero_personas_efectivo IS NULL OR p.tiempo_parada_efectivo_min IS NULL
              ) AS planes_pendientes
            FROM programacion.orden_mantenimiento o
            JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.periodo=:period
        """),{"period":period}).mappings().one()

        specialties=[dict(r) for r in conn.execute(text("""
            SELECT
              COALESCE(o.especialidad,'SIN') AS especialidad,
              count(*) AS registros,
              count(DISTINCT o.numero_ot) FILTER (WHERE o.numero_ot IS NOT NULL) AS ot_distintas,
              round(COALESCE(sum(
                COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)
                / 60.0 * p.numero_personas_efectivo
              ) FILTER (
                WHERE p.numero_personas_efectivo IS NOT NULL
                  AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
              ),0),2) AS hh_calculables
            FROM programacion.orden_mantenimiento o
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.periodo=:period
            GROUP BY COALESCE(o.especialidad,'SIN')
            ORDER BY especialidad
        """),{"period":period}).mappings()]

        areas=[dict(r) for r in conn.execute(text("""
            WITH codes AS (
              SELECT area_codigo,count(*) AS equipos
              FROM programacion.activo
              WHERE area_codigo IS NOT NULL
              GROUP BY area_codigo
            )
            SELECT
              c.area_codigo AS codigo,
              root.descripcion AS nombre,
              c.equipos
            FROM codes c
            LEFT JOIN programacion.activo root
              ON root.codigo='BA-'||c.area_codigo
            ORDER BY c.area_codigo
        """)).mappings()]

    return {
        "periodo":str(period),
        "summary":dict(summary),
        "pending":dict(pending),
        "specialties":specialties,
        "areas":areas,
    }


def get_pending_plans(year:int,month:int,specialty:str|None=None)->dict[str,Any]:
    period=_period(year,month)
    params={"period":period}
    spec_clause=""
    if specialty:
        specialty=specialty.upper()
        if specialty not in VALID_SPECIALTIES:
            raise ValueError("Especialidad inválida")
        params["specialty"]=specialty
        spec_clause=" AND p.especialidad=:specialty "

    with get_engine().connect() as conn:
        rows=[dict(r) for r in conn.execute(text(f"""
            SELECT
              p.id,
              p.grupo,
              p.descripcion_grupo,
              p.plan_trabajo,
              p.descripcion_plan_trabajo,
              p.especialidad,
              p.tiempo_ejecucion_min,
              p.numero_personas AS numero_personas_software,
              p.numero_personas_app,
              p.numero_personas_efectivo,
              p.tiempo_parada_min AS tiempo_parada_software,
              p.tiempo_parada_app_min,
              p.tiempo_parada_efectivo_min,
              p.requiere_parada,
              count(o.id) AS registros_pmp,
              count(DISTINCT o.numero_ot) FILTER (WHERE o.numero_ot IS NOT NULL) AS ot_distintas
            FROM programacion.plan_trabajo p
            JOIN programacion.orden_mantenimiento o ON o.plan_trabajo_id=p.id
            WHERE o.periodo=:period
              AND (
                p.numero_personas_efectivo IS NULL
                OR p.tiempo_parada_efectivo_min IS NULL
              )
              {spec_clause}
            GROUP BY p.id
            ORDER BY count(o.id) DESC,p.descripcion_grupo,p.plan_trabajo
        """),params).mappings()]

        missing_master=[dict(r) for r in conn.execute(text("""
            SELECT
              plan_clave_software,
              count(*) AS registros_pmp,
              count(DISTINCT numero_ot) FILTER (WHERE numero_ot IS NOT NULL) AS ot_distintas
            FROM programacion.orden_mantenimiento
            WHERE periodo=:period AND plan_trabajo_id IS NULL
            GROUP BY plan_clave_software
            ORDER BY count(*) DESC,plan_clave_software
        """),{"period":period}).mappings()]

    return {"periodo":str(period),"plans":rows,"missing_master":missing_master}


def save_plan_complement(
    plan_id:int,
    *,
    people:float|None,
    stop_minutes:float|None,
)->dict[str,Any]:
    if people is not None and people<=0:
        raise ValueError("Número de personas debe ser mayor que 0")
    if stop_minutes is not None and stop_minutes<0:
        raise ValueError("Tiempo de parada no puede ser negativo")

    with get_engine().begin() as conn:
        current=conn.execute(text("""
            SELECT id,numero_personas,tiempo_parada_min
            FROM programacion.plan_trabajo
            WHERE id=:id
        """),{"id":plan_id}).mappings().first()
        if not current:
            raise ValueError("Plan de trabajo no encontrado")

        conn.execute(text("""
            UPDATE programacion.plan_trabajo
            SET numero_personas_app=CASE
                  WHEN numero_personas IS NULL THEN :people
                  ELSE numero_personas_app
                END,
                tiempo_parada_app_min=CASE
                  WHEN tiempo_parada_min IS NULL THEN :stop
                  ELSE tiempo_parada_app_min
                END,
                complementado_en=now()
            WHERE id=:id
        """),{"people":people,"stop":stop_minutes,"id":plan_id})

        row=conn.execute(text("""
            SELECT id,grupo,descripcion_grupo,plan_trabajo,especialidad,
                   numero_personas,numero_personas_app,numero_personas_efectivo,
                   tiempo_parada_min,tiempo_parada_app_min,tiempo_parada_efectivo_min,
                   requiere_parada,complementado_en
            FROM programacion.plan_trabajo
            WHERE id=:id
        """),{"id":plan_id}).mappings().one()

    return dict(row)


def get_technicians(year:int,month:int)->dict[str,Any]:
    period=_period(year,month)
    with get_engine().connect() as conn:
        rows=[dict(r) for r in conn.execute(text("""
            SELECT
              t.id,t.identificacion,t.nombre,
              t.especialidad AS especialidad_software,
              t.especialidad_app,t.especialidad_efectiva,
              round(COALESCE(sum(pt.horas_disponibles),0),2) AS hh_mes,
              count(pt.id) AS registros_turno
            FROM programacion.tecnico t
            LEFT JOIN programacion.programacion_tecnico pt
              ON pt.tecnico_id=t.id
             AND date_trunc('month',pt.fecha)::date=:period
            GROUP BY t.id
            ORDER BY COALESCE(t.especialidad_efectiva,'ZZZ'),t.nombre
        """),{"period":period}).mappings()]
    return {"periodo":str(period),"technicians":rows}


def save_technician_complement(technician_id:int,specialty:str)->dict[str,Any]:
    specialty=specialty.upper()
    if specialty not in VALID_SPECIALTIES:
        raise ValueError("Especialidad inválida")
    with get_engine().begin() as conn:
        current=conn.execute(text("""
            SELECT id,especialidad
            FROM programacion.tecnico
            WHERE id=:id
        """),{"id":technician_id}).mappings().first()
        if not current:
            raise ValueError("Técnico no encontrado")
        conn.execute(text("""
            UPDATE programacion.tecnico
            SET especialidad_app=CASE WHEN especialidad IS NULL THEN :specialty ELSE especialidad_app END,
                complementado_en=now()
            WHERE id=:id
        """),{"specialty":specialty,"id":technician_id})
        row=conn.execute(text("""
            SELECT id,identificacion,nombre,especialidad AS especialidad_software,
                   especialidad_app,especialidad_efectiva,complementado_en
            FROM programacion.tecnico WHERE id=:id
        """),{"id":technician_id}).mappings().one()
    return dict(row)


def get_pmp(
    year:int,
    month:int,
    *,
    specialty:str|None=None,
    area:str|None=None,
    search:str|None=None,
    limit:int=300,
)->dict[str,Any]:
    period=_period(year,month)
    limit=max(1,min(limit,1000))
    params={"period":period,"limit":limit}
    clauses=["o.periodo=:period"]

    if specialty:
        specialty=specialty.upper()
        if specialty not in VALID_SPECIALTIES:
            raise ValueError("Especialidad inválida")
        clauses.append("o.especialidad=:specialty")
        params["specialty"]=specialty
    if area:
        clauses.append("a.area_codigo=:area")
        params["area"]=area.upper()
    if search:
        clauses.append("""
          (
            COALESCE(o.numero_ot,'') ILIKE :search
            OR a.codigo ILIKE :search
            OR COALESCE(a.descripcion,'') ILIKE :search
            OR o.plan_clave_software ILIKE :search
            OR COALESCE(p.plan_trabajo,'') ILIKE :search
          )
        """)
        params["search"]=f"%{search.strip()}%"

    where=" AND ".join(clauses)
    with get_engine().connect() as conn:
        rows=[dict(r) for r in conn.execute(text(f"""
            SELECT
              o.id,o.numero_ot,o.estado,o.especialidad,o.titulo,
              a.codigo AS activo_codigo,a.descripcion AS activo_descripcion,
              a.area_codigo,
              root.descripcion AS area_nombre,
              o.plan_clave_software,
              p.id AS plan_trabajo_id,
              p.plan_trabajo,
              p.descripcion_grupo,
              p.numero_personas_efectivo,
              p.tiempo_parada_efectivo_min,
              p.requiere_parada,
              COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) AS tiempo_min,
              CASE
                WHEN p.id IS NULL THEN NULL
                WHEN p.numero_personas_efectivo IS NULL THEN NULL
                WHEN COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NULL THEN NULL
                ELSE round(
                  COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)
                  / 60.0 * p.numero_personas_efectivo
                ,2)
              END AS hh,
              CASE
                WHEN p.id IS NULL THEN 'PLAN NO MAESTRO'
                WHEN p.numero_personas_efectivo IS NULL THEN 'FALTA PERSONAS'
                WHEN p.tiempo_parada_efectivo_min IS NULL THEN 'FALTA PARADA'
                WHEN COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NULL THEN 'FALTA TIEMPO'
                ELSE 'LISTO'
              END AS calidad_dato
            FROM programacion.orden_mantenimiento o
            JOIN programacion.activo a ON a.id=o.activo_id
            LEFT JOIN programacion.activo root ON root.codigo='BA-'||a.area_codigo
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE {where}
            ORDER BY o.especialidad,a.area_codigo,o.numero_ot NULLS LAST,o.id
            LIMIT :limit
        """),params).mappings()]

    return {"periodo":str(period),"rows":rows,"limit":limit}
