from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.services.v2_programming_service import refresh_open_program_capacities


VALID_SPECIALTIES={"MEC","ELE","MET","SER"}


def _period(year:int,month:int)->date:
    if year<2020 or year>2100 or month<1 or month>12:
        raise ValueError("Periodo inválido")
    return date(year,month,1)


def _dashboard_progress_payload(row:dict[str,Any])->dict[str,Any]:
    total=max(0,int(row.get("total_orders") or 0))
    finalized=max(0,min(total,int(row.get("finalized_orders") or 0)))
    pending=max(0,total-finalized)
    return {
        "total_orders":total,
        "finalized_orders":finalized,
        "pending_orders":pending,
        "progress_pct":round(100.0*finalized/total,1) if total else 0.0,
        "pmp_orders":max(0,int(row.get("pmp_orders") or 0)),
        "backlog_orders":max(0,int(row.get("backlog_orders") or 0)),
        "latest_tracking_at":row.get("latest_tracking_at"),
    }


def get_dashboard(year:int,month:int)->dict[str,Any]:
    period=_period(year,month)
    next_period=date(year+1,1,1) if month==12 else date(year,month+1,1)
    with get_engine().connect() as conn:
        summary=conn.execute(text("""
            WITH month_orders AS (
              SELECT o.*,p.numero_personas_efectivo,p.tiempo_parada_efectivo_min,
                     p.tiempo_ejecucion_min,p.requiere_parada
              FROM programacion.orden_mantenimiento o
              LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              WHERE o.periodo=:period AND COALESCE(p.es_operacion,false)=false
            )
            SELECT
              (SELECT count(*) FROM programacion.activo) AS activos,
              (SELECT count(*) FROM programacion.plan_trabajo WHERE NOT es_operacion) AS planes,
              (SELECT count(*) FROM programacion.plan_trabajo WHERE es_operacion) AS planes_operacion,
              (SELECT count(*) FROM programacion.orden_mantenimiento xo JOIN programacion.plan_trabajo xp ON xp.id=xo.plan_trabajo_id WHERE xo.periodo=:period AND xp.es_operacion) AS registros_operacion_excluidos,
              (SELECT count(*) FROM programacion.planeacion) AS planeaciones,
              count(id) AS registros_pmp,
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
            WHERE o.periodo=:period AND COALESCE(p.es_operacion,false)=false
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
            WHERE o.periodo=:period AND COALESCE(p.es_operacion,false)=false
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

        workload=conn.execute(text("""
            WITH pmp_candidate AS (
              SELECT
                o.id AS orden_mantenimiento_id,
                CASE
                  WHEN p.numero_personas_efectivo IS NOT NULL
                   AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
                  THEN round(COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0*p.numero_personas_efectivo,2)
                  ELSE NULL
                END AS hh,
                (
                  upper(COALESCE(o.estado,'')) LIKE 'FINALIZ%'
                  OR EXISTS (
                    SELECT 1
                    FROM programacion.programacion_item_v2 pi
                    JOIN programacion.programacion_semanal_v2 ps ON ps.id=pi.programacion_id
                    WHERE pi.orden_mantenimiento_id=o.id
                      AND (ps.estado<>'CERRADA' OR COALESCE(pi.finalizado,false)=true)
                  )
                ) AS cubierta
              FROM programacion.orden_mantenimiento o
              LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              WHERE o.periodo=:period AND COALESCE(p.es_operacion,false)=false
            ),
            pmp_pending AS (
              SELECT orden_mantenimiento_id,hh
              FROM pmp_candidate
              WHERE NOT cubierta
            ),
            backlog_pending AS (
              SELECT DISTINCT
                o.id AS orden_mantenimiento_id,
                CASE
                  WHEN p.numero_personas_efectivo IS NOT NULL
                   AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
                  THEN round(COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0*p.numero_personas_efectivo,2)
                  ELSE NULL
                END AS hh
              FROM programacion.backlog_v2 b
              JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
              LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              WHERE b.estado_seguimiento='PENDIENTE_DISPONIBLE'
                AND upper(COALESCE(o.estado,'')) NOT LIKE 'FINALIZ%'
                AND COALESCE(p.es_operacion,false)=false
            ),
            all_pending AS (
              SELECT orden_mantenimiento_id,max(hh) AS hh
              FROM (
                SELECT * FROM pmp_pending
                UNION ALL
                SELECT * FROM backlog_pending
              ) x
              GROUP BY orden_mantenimiento_id
            )
            SELECT
              (SELECT count(*) FROM pmp_pending)::int AS pmp_pending_count,
              round(COALESCE((SELECT sum(hh) FROM pmp_pending),0),2) AS pmp_pending_hh,
              (SELECT count(*) FROM backlog_pending)::int AS backlog_available_count,
              round(COALESCE((SELECT sum(hh) FROM backlog_pending),0),2) AS backlog_available_hh,
              count(*)::int AS total_pending_count,
              round(COALESCE(sum(hh),0),2) AS total_pending_hh,
              count(*) FILTER (WHERE hh IS NULL)::int AS total_missing_hh_count
            FROM all_pending
        """),{"period":period}).mappings().one()

        progress_row=dict(conn.execute(text("""
            WITH month_pmp AS (
              SELECT DISTINCT o.id AS order_id
              FROM programacion.orden_mantenimiento o
              LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              WHERE o.periodo=:period
                AND COALESCE(p.es_operacion,false)=false
            ),
            backlog_available AS (
              SELECT DISTINCT b.orden_mantenimiento_id AS order_id
              FROM programacion.backlog_v2 b
              JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
              LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              WHERE b.estado_seguimiento='PENDIENTE_DISPONIBLE'
                AND COALESCE(p.es_operacion,false)=false
            ),
            backlog_used_month AS (
              SELECT DISTINCT pi.orden_mantenimiento_id AS order_id
              FROM programacion.programacion_item_v2 pi
              JOIN programacion.programacion_semanal_v2 ps ON ps.id=pi.programacion_id
              JOIN programacion.orden_mantenimiento o ON o.id=pi.orden_mantenimiento_id
              LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              WHERE ps.semana_inicio>=:period
                AND ps.semana_inicio<:next_period
                AND COALESCE(pi.origen_backlog,false)=true
                AND COALESCE(p.es_operacion,false)=false
            ),
            universe AS (
              SELECT DISTINCT order_id
              FROM (
                SELECT order_id FROM month_pmp
                UNION ALL
                SELECT order_id FROM backlog_available
                UNION ALL
                SELECT order_id FROM backlog_used_month
              ) all_orders
            ),
            tracked_finalized AS (
              SELECT DISTINCT si.orden_mantenimiento_id AS order_id
              FROM programacion.seguimiento_semanal_item_v2 si
              JOIN programacion.seguimiento_semanal_v2 s ON s.id=si.seguimiento_id
              JOIN programacion.programacion_semanal_v2 ps ON ps.id=s.programacion_id
              WHERE ps.semana_inicio>=:period
                AND ps.semana_inicio<:next_period
                AND si.finalizado=true
            ),
            closed_finalized AS (
              SELECT DISTINCT pi.orden_mantenimiento_id AS order_id
              FROM programacion.programacion_item_v2 pi
              JOIN programacion.programacion_semanal_v2 ps ON ps.id=pi.programacion_id
              WHERE ps.semana_inicio>=:period
                AND ps.semana_inicio<:next_period
                AND ps.estado='CERRADA'
                AND pi.finalizado=true
            ),
            finished AS (
              SELECT order_id FROM tracked_finalized
              UNION
              SELECT order_id FROM closed_finalized
            ),
            latest_tracking AS (
              SELECT max(s.registrado_en) AS latest_tracking_at
              FROM programacion.seguimiento_semanal_v2 s
              JOIN programacion.programacion_semanal_v2 ps ON ps.id=s.programacion_id
              WHERE ps.semana_inicio>=:period
                AND ps.semana_inicio<:next_period
            )
            SELECT
              (SELECT count(*) FROM universe)::int AS total_orders,
              (
                SELECT count(*)
                FROM finished f
                JOIN universe u USING(order_id)
              )::int AS finalized_orders,
              (SELECT count(*) FROM month_pmp)::int AS pmp_orders,
              (
                SELECT count(*)
                FROM universe u
                WHERE NOT EXISTS (
                  SELECT 1 FROM month_pmp p WHERE p.order_id=u.order_id
                )
              )::int AS backlog_orders,
              (SELECT latest_tracking_at FROM latest_tracking) AS latest_tracking_at
        """),{"period":period,"next_period":next_period}).mappings().one())
        tracking_progress=_dashboard_progress_payload(progress_row)

    return {
        "periodo":str(period),
        "summary":dict(summary),
        "pending":dict(pending),
        "workload":dict(workload),
        "tracking_progress":tracking_progress,
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
            WHERE o.periodo=:period AND COALESCE(p.es_operacion,false)=false
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


def save_technician_complement(technician_id:int,specialty:str|None)->dict[str,Any]:
    specialty=(specialty or "").strip().upper() or None
    if specialty is not None and specialty not in VALID_SPECIALTIES:
        raise ValueError("Especialidad inválida")
    with get_engine().begin() as conn:
        current=conn.execute(text("""
            SELECT id,especialidad,especialidad_app,especialidad_efectiva
            FROM programacion.tecnico
            WHERE id=:id
        """),{"id":technician_id}).mappings().first()
        if not current:
            raise ValueError("Técnico no encontrado")
        conn.execute(text("""
            UPDATE programacion.tecnico
            SET especialidad_app=:specialty,
                complementado_en=now()
            WHERE id=:id
        """),{"specialty":specialty,"id":technician_id})
        refreshed_programs=refresh_open_program_capacities(conn)
        row=conn.execute(text("""
            SELECT id,identificacion,nombre,especialidad AS especialidad_software,
                   especialidad_app,especialidad_efectiva,complementado_en
            FROM programacion.tecnico WHERE id=:id
        """),{"id":technician_id}).mappings().one()
    result=dict(row)
    result["programaciones_recalculadas"]=int(refreshed_programs)
    return result


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
    clauses=["o.periodo=:period", "COALESCE(p.es_operacion,false)=false"]

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
