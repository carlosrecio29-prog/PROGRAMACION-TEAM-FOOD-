from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.services.v2_programming_service import (
    V2ProgrammingError,
    _capacity,
    _validate_week,
    export_weekly_excel,
    export_weekly_pdf,
)


def get_week_programming(*, date_from: date, date_to: date, specialty: str) -> dict[str, Any]:
    specialty = _validate_week(date_from, date_to, specialty)
    with get_engine().connect() as conn:
        capacity = _capacity(conn, date_from, date_to, specialty)
        programming = conn.execute(text("""
            SELECT id,estado,hh_disponibles,hh_objetivo,hh_reserva,creado_en,actualizado_en,emitido_en,
                   cierre_en,cierre_por,cierre_archivo,cierre_total,cierre_finalizadas,cierre_pendientes,cierre_no_encontradas
            FROM programacion.programacion_semanal_v2
            WHERE semana_inicio=:date_from AND semana_fin=:date_to AND especialidad=:specialty
        """), {"date_from": date_from, "date_to": date_to, "specialty": specialty}).mappings().first()
        programming_id = int(programming["id"]) if programming else None

        rows = [dict(r) for r in conn.execute(text("""
            WITH candidate AS (
              SELECT DISTINCT ON (o.id)
                o.id AS orden_mantenimiento_id,o.numero_ot,o.titulo,o.estado,o.especialidad,o.periodo,
                a.codigo AS activo_codigo,a.descripcion AS activo_descripcion,a.area_codigo,root.descripcion AS area_nombre,
                p.id AS plan_trabajo_id,p.plan_trabajo,p.descripcion_grupo,p.numero_personas_efectivo,
                p.tiempo_parada_efectivo_min,p.requiere_parada,
                COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) AS tiempo_min,
                round(COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0*p.numero_personas_efectivo,2) AS hh,
                b.id AS backlog_id,b.semana_origen_inicio,b.semana_origen_fin,b.movido_en
              FROM programacion.orden_mantenimiento o
              JOIN programacion.activo a ON a.id=o.activo_id
              LEFT JOIN programacion.activo root ON root.codigo='BA-'||a.area_codigo
              JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              LEFT JOIN programacion.backlog_v2 b ON b.orden_mantenimiento_id=o.id AND b.especialidad=:specialty
              LEFT JOIN programacion.programacion_item_v2 ci
                ON ci.orden_mantenimiento_id=o.id AND ci.programacion_id=CAST(:programming_id AS bigint)
              WHERE o.especialidad=:specialty
                AND (o.periodo=date_trunc('month',CAST(:date_from AS date))::date OR b.id IS NOT NULL OR ci.id IS NOT NULL)
                AND (upper(COALESCE(o.estado,''))<>'FINALIZADO' OR ci.id IS NOT NULL)
                AND p.numero_personas_efectivo IS NOT NULL
                AND p.tiempo_parada_efectivo_min IS NOT NULL
                AND p.requiere_parada IS NOT NULL
                AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
              ORDER BY o.id,b.movido_en DESC NULLS LAST
            )
            SELECT c.*,
              CASE WHEN current_item.id IS NOT NULL THEN true ELSE false END AS seleccionado,
              CASE WHEN c.backlog_id IS NOT NULL AND current_item.id IS NULL THEN true ELSE false END AS es_backlog,
              CASE WHEN current_item.id IS NOT NULL THEN current_item.origen_backlog ELSE c.backlog_id IS NOT NULL END AS origen_backlog,
              CASE
                WHEN current_item.id IS NOT NULL THEN current_item.origen
                WHEN c.backlog_id IS NOT NULL THEN 'BACKLOG'
                ELSE 'PMP_MES'
              END AS origen,
              current_item.estado_cierre,current_item.finalizado,current_item.verificado_en
            FROM candidate c
            LEFT JOIN programacion.programacion_item_v2 current_item
              ON current_item.orden_mantenimiento_id=c.orden_mantenimiento_id
             AND current_item.programacion_id=CAST(:programming_id AS bigint)
            WHERE NOT EXISTS (
              SELECT 1
              FROM programacion.programacion_item_v2 other_item
              JOIN programacion.programacion_semanal_v2 other_program ON other_program.id=other_item.programacion_id
              WHERE other_item.orden_mantenimiento_id=c.orden_mantenimiento_id
                AND other_program.estado<>'CERRADA'
                AND (CAST(:programming_id AS bigint) IS NULL OR other_program.id<>CAST(:programming_id AS bigint))
            )
            ORDER BY c.area_codigo,c.numero_ot NULLS LAST,c.activo_codigo,c.plan_trabajo
        """), {"date_from": date_from, "specialty": specialty, "programming_id": programming_id}).mappings()]

        selected_hh = round(sum(float(r["hh"] or 0) for r in rows if r["seleccionado"]), 2)

    backlog = [r for r in rows if r["es_backlog"]]
    regular = [r for r in rows if not r["es_backlog"]]
    operating = [r for r in regular if r["requiere_parada"] is False]
    stopped = [r for r in regular if r["requiere_parada"] is True]
    return {
        "date_from": str(date_from), "date_to": str(date_to), "specialty": specialty,
        "capacity": capacity, "programming": dict(programming) if programming else None,
        "selected_hh": selected_hh,
        "selected_ids": [int(r["orden_mantenimiento_id"]) for r in rows if r["seleccionado"]],
        "operating": operating, "stopped": stopped, "backlog": backlog, "backlog_count": len(backlog),
    }


def save_week_programming(*, date_from: date, date_to: date, specialty: str, order_ids: list[int], created_by: str | None = None) -> dict[str, Any]:
    specialty = _validate_week(date_from, date_to, specialty)
    unique_ids = list(dict.fromkeys(int(x) for x in order_ids))
    if not unique_ids:
        raise V2ProgrammingError("Debes seleccionar al menos una orden/actividad")

    with get_engine().begin() as conn:
        capacity = _capacity(conn, date_from, date_to, specialty)
        if capacity["target"] <= 0:
            raise V2ProgrammingError("Esta especialidad no tiene H-H disponibles para la semana seleccionada")

        current = conn.execute(text("""
            SELECT id,estado FROM programacion.programacion_semanal_v2
            WHERE semana_inicio=:date_from AND semana_fin=:date_to AND especialidad=:specialty
        """), {"date_from": date_from, "date_to": date_to, "specialty": specialty}).mappings().first()
        current_id = int(current["id"]) if current else None
        if current and current["estado"] == "CERRADA":
            raise V2ProgrammingError("Esta semana ya fue cerrada. Las OT pendientes deben programarse desde BACKLOG en una semana nueva.")

        previous_ids: list[int] = []
        previous_origins: set[int] = set()
        if current_id:
            previous = conn.execute(text("""
                SELECT orden_mantenimiento_id,origen_backlog
                FROM programacion.programacion_item_v2 WHERE programacion_id=:id
            """), {"id": current_id}).mappings().all()
            previous_ids = [int(x["orden_mantenimiento_id"]) for x in previous]
            previous_origins = {int(x["orden_mantenimiento_id"]) for x in previous if x["origen_backlog"]}

        backlog_ids = {int(x) for x in conn.execute(text("""
            SELECT orden_mantenimiento_id FROM programacion.backlog_v2
            WHERE orden_mantenimiento_id=ANY(CAST(:ids AS bigint[]))
        """), {"ids": unique_ids}).scalars().all()}

        rows = [dict(r) for r in conn.execute(text("""
            SELECT o.id AS orden_mantenimiento_id,o.numero_ot,p.requiere_parada,
              round(COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0*p.numero_personas_efectivo,2) AS hh
            FROM programacion.orden_mantenimiento o
            JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.id=ANY(CAST(:ids AS bigint[])) AND o.especialidad=:specialty
              AND upper(COALESCE(o.estado,''))<>'FINALIZADO'
              AND p.numero_personas_efectivo IS NOT NULL AND p.tiempo_parada_efectivo_min IS NOT NULL
              AND p.requiere_parada IS NOT NULL AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
        """), {"ids": unique_ids, "specialty": specialty}).mappings()]
        if len(rows) != len(unique_ids):
            raise V2ProgrammingError("Una o más órdenes ya no están disponibles o tienen datos incompletos")

        conflicts = conn.execute(text("""
            SELECT o.numero_ot,ps.semana_inicio,ps.semana_fin,ps.especialidad
            FROM programacion.programacion_item_v2 pi
            JOIN programacion.programacion_semanal_v2 ps ON ps.id=pi.programacion_id
            JOIN programacion.orden_mantenimiento o ON o.id=pi.orden_mantenimiento_id
            WHERE pi.orden_mantenimiento_id=ANY(CAST(:ids AS bigint[]))
              AND ps.estado<>'CERRADA'
              AND (CAST(:current_id AS bigint) IS NULL OR ps.id<>CAST(:current_id AS bigint))
            LIMIT 10
        """), {"ids": unique_ids, "current_id": current_id}).mappings().all()
        if conflicts:
            first = conflicts[0]
            raise V2ProgrammingError(f"La OT {first['numero_ot'] or 'SIN ASIGNAR'} ya está programada del {first['semana_inicio']} al {first['semana_fin']}")

        total = round(sum(float(r["hh"] or 0) for r in rows), 2)
        if total > capacity["target"] + .001:
            raise V2ProgrammingError(f"La selección suma {total:.1f} H-H y supera la meta del 80% ({capacity['target']:.1f} H-H)")

        programming_id = conn.execute(text("""
            INSERT INTO programacion.programacion_semanal_v2(
              semana_inicio,semana_fin,especialidad,hh_disponibles,hh_objetivo,hh_reserva,estado,creado_por,actualizado_en
            ) VALUES(:date_from,:date_to,:specialty,:available,:target,:reserve,'GUARDADA',:created_by,now())
            ON CONFLICT(semana_inicio,semana_fin,especialidad)
            DO UPDATE SET hh_disponibles=EXCLUDED.hh_disponibles,hh_objetivo=EXCLUDED.hh_objetivo,
              hh_reserva=EXCLUDED.hh_reserva,estado='GUARDADA',
              creado_por=COALESCE(EXCLUDED.creado_por,programacion.programacion_semanal_v2.creado_por),actualizado_en=now()
            RETURNING id
        """), {"date_from": date_from, "date_to": date_to, "specialty": specialty,
                 "available": capacity["available"], "target": capacity["target"], "reserve": capacity["reserve"], "created_by": created_by}).scalar_one()

        removed_ids = sorted(set(previous_ids) - set(unique_ids))
        if removed_ids:
            conn.execute(text("""
                INSERT INTO programacion.backlog_v2(
                  orden_mantenimiento_id,programacion_origen_id,semana_origen_inicio,semana_origen_fin,
                  especialidad,motivo,movido_por,movido_en,actualizado_en
                )
                SELECT x,:programming_id,:date_from,:date_to,:specialty,'RETIRADA DE PROGRAMACIÓN SEMANAL',:created_by,now(),now()
                FROM unnest(CAST(:removed_ids AS bigint[])) AS x
                ON CONFLICT(orden_mantenimiento_id)
                DO UPDATE SET programacion_origen_id=EXCLUDED.programacion_origen_id,
                  semana_origen_inicio=EXCLUDED.semana_origen_inicio,semana_origen_fin=EXCLUDED.semana_origen_fin,
                  especialidad=EXCLUDED.especialidad,motivo=EXCLUDED.motivo,movido_por=EXCLUDED.movido_por,
                  movido_en=now(),actualizado_en=now()
            """), {"programming_id": programming_id, "date_from": date_from, "date_to": date_to,
                     "specialty": specialty, "created_by": created_by, "removed_ids": removed_ids})

        conn.execute(text("DELETE FROM programacion.backlog_v2 WHERE orden_mantenimiento_id=ANY(CAST(:ids AS bigint[]))"), {"ids": unique_ids})
        conn.execute(text("DELETE FROM programacion.programacion_item_v2 WHERE programacion_id=:programming_id"), {"programming_id": programming_id})
        for row in rows:
            order_id = int(row["orden_mantenimiento_id"])
            origin_backlog = order_id in backlog_ids or order_id in previous_origins
            origin = "BACKLOG" if origin_backlog else "PMP_MES"
            conn.execute(text("""
                INSERT INTO programacion.programacion_item_v2(
                  programacion_id,orden_mantenimiento_id,hh_programadas,requiere_parada,origen_backlog,origen
                ) VALUES(:programming_id,:order_id,:hh,:requires_stop,:origin_backlog,:origin)
            """), {"programming_id": programming_id, "order_id": order_id, "hh": row["hh"],
                     "requires_stop": row["requiere_parada"], "origin_backlog": origin_backlog, "origin": origin})

    return {
        "ok": True, "programming_id": int(programming_id), "hh_available": capacity["available"],
        "hh_target": capacity["target"], "hh_reserve": capacity["reserve"], "hh_programmed": total,
        "progress_pct": round(total / capacity["target"] * 100, 1) if capacity["target"] else 0,
        "items": len(rows), "moved_to_backlog": len(removed_ids),
    }
