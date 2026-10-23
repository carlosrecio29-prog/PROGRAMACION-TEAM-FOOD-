from __future__ import annotations

from typing import Any

from sqlalchemy import text

from backend.database import get_engine

VALID_BACKLOG_STATES = {
    "PENDIENTE_DISPONIBLE",
    "PENDIENTE_PROGRAMADA",
    "FINALIZADA",
    "ANULADA",
}


def _build_backlog_filters(
    *, specialty: str | None = None, area: str | None = None, state: str | None = None,
    search: str | None = None, order_id: int | None = None,
    age_min: int | None = None, age_max: int | None = None,
) -> tuple[str, dict[str, Any]]:
    clauses = ["1=1"]
    params: dict[str, Any] = {}
    if specialty:
        clauses.append("b.especialidad=:specialty")
        params["specialty"] = specialty.strip().upper()
    if area:
        clauses.append("a.area_codigo=:area")
        params["area"] = area.strip()
    if state:
        normalized_state = state.strip().upper()
        if normalized_state not in VALID_BACKLOG_STATES:
            raise ValueError("Estado de backlog inválido")
        clauses.append("b.estado_seguimiento=:state")
        params["state"] = normalized_state
    else:
        clauses.append("b.estado_seguimiento IN ('PENDIENTE_DISPONIBLE','PENDIENTE_PROGRAMADA')")
    if not state or normalized_state in {'PENDIENTE_DISPONIBLE', 'PENDIENTE_PROGRAMADA'}:
        clauses.append("upper(COALESCE(o.estado,'')) NOT LIKE 'ANUL%'")
        clauses.append("upper(COALESCE(o.estado,'')) NOT LIKE 'FINALIZ%'")
    if order_id is not None:
        clauses.append("b.orden_mantenimiento_id=:order_id")
        params["order_id"] = order_id
    if search and search.strip():
        clauses.append("concat_ws(' ',o.numero_ot,a.codigo,a.descripcion,p.plan_trabajo,o.titulo,o.plan_clave_software,b.motivo) ILIKE :search")
        params["search"] = f"%{search.strip()}%"
    age_expression = "GREATEST(0,(CURRENT_TIMESTAMP AT TIME ZONE 'America/Bogota')::date-COALESCE(b.primera_semana_origen_inicio,b.semana_origen_inicio))"
    if age_min is not None:
        clauses.append(f"{age_expression}>=:age_min")
        params["age_min"] = age_min
    if age_max is not None:
        clauses.append(f"{age_expression}<=:age_max")
        params["age_max"] = age_max
    return " AND ".join(clauses), params


def get_accumulated_backlog(
    *, specialty: str | None = None, area: str | None = None, state: str | None = None,
    search: str | None = None, order_id: int | None = None,
    age_min: int | None = None, age_max: int | None = None, limit: int = 300,
) -> dict[str, Any]:
    if age_min is not None and age_max is not None and age_min > age_max:
        raise ValueError("La antigüedad mínima no puede superar la máxima")
    where, params = _build_backlog_filters(
        specialty=specialty, area=area, state=state, search=search,
        order_id=order_id, age_min=age_min, age_max=age_max,
    )
    params["limit"] = limit
    with get_engine().connect() as conn:
        rows = [dict(row) for row in conn.execute(text(f"""
            SELECT b.id,b.orden_mantenimiento_id,b.especialidad,b.estado_seguimiento,b.motivo,
                   b.semana_origen_inicio,b.semana_origen_fin,b.primera_semana_origen_inicio,
                   b.primera_semana_origen_fin,b.movido_en,b.ultimo_resultado_cierre,b.ultimo_cierre_en,
                   b.reprogramaciones,b.finalizado_en,b.finalizado_por,
                   o.numero_ot,o.periodo AS periodo_origen,a.codigo AS activo_codigo,a.descripcion AS activo_descripcion,a.area_codigo,
                   COALESCE(p.plan_trabajo,o.titulo,o.plan_clave_software) AS plan_trabajo,
                   p.descripcion_grupo,
                   round(COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0*p.numero_personas_efectivo,2) AS hh,
                   GREATEST(0,(CURRENT_TIMESTAMP AT TIME ZONE 'America/Bogota')::date-COALESCE(b.primera_semana_origen_inicio,b.semana_origen_inicio)) AS antiguedad_dias
            FROM programacion.backlog_v2 b
            JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
            JOIN programacion.activo a ON a.id=o.activo_id
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE {where} AND COALESCE(p.es_operacion,false)=false
            ORDER BY b.primera_semana_origen_inicio ASC,b.movido_en ASC,o.numero_ot NULLS LAST
            LIMIT :limit
        """), params).mappings()]
        summary = _get_backlog_summary(conn)
        filtered_summary = _get_backlog_summary(conn, where=where, params=params)
    return {"rows": rows, "summary": summary, "filtered_summary": filtered_summary}


def _get_backlog_summary(conn, *, where: str = "1=1", params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Summaries declare their scope: global history or the requested row filters."""
    active = """b.estado_seguimiento IN ('PENDIENTE_DISPONIBLE','PENDIENTE_PROGRAMADA')
                AND upper(COALESCE(o.estado,'')) NOT LIKE 'ANUL%'
                AND upper(COALESCE(o.estado,'')) NOT LIKE 'FINALIZ%'"""
    return dict(conn.execute(text(f"""
            SELECT
              count(*) AS movidas,
              count(*) FILTER (WHERE b.estado_seguimiento='FINALIZADA') AS finalizadas_por_ingeniero,
              count(*) FILTER (WHERE b.estado_seguimiento='ANULADA') AS anuladas,
              count(*) FILTER (WHERE {active} AND b.estado_seguimiento='PENDIENTE_DISPONIBLE') AS disponibles,
              count(*) FILTER (WHERE {active} AND b.estado_seguimiento='PENDIENTE_PROGRAMADA') AS programadas,
              count(*) FILTER (
                WHERE {active}
                  AND COALESCE(p.es_operacion,false)=false
              ) AS pendientes_activas,
              count(*) FILTER (
                WHERE {active}
                  AND upper(COALESCE(b.motivo,'')) LIKE 'ARRASTRE INICIAL%'
                  AND COALESCE(p.es_operacion,false)=false
              ) AS carga_inicial,
              round(COALESCE(sum(
                COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0
                * p.numero_personas_efectivo
              ) FILTER (
                WHERE {active}
                  AND COALESCE(p.es_operacion,false)=false
                  AND p.numero_personas_efectivo IS NOT NULL
                  AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
              ),0),2) AS hh_backlog_activo,
              count(*) FILTER (
                WHERE {active}
                  AND COALESCE(p.es_operacion,false)=false
                  AND (
                    p.numero_personas_efectivo IS NULL
                    OR COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NULL
                  )
              ) AS backlog_sin_hh
            FROM programacion.backlog_v2 b
            JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
            JOIN programacion.activo a ON a.id=o.activo_id
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE {where} AND COALESCE(p.es_operacion,false)=false
        """), params or {}).mappings().one())
