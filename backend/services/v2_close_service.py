from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.parsers.common import normalize_text
from backend.services.v2_import_service import _parse_monthly


class V2CloseError(ValueError):
    pass


def _norm(value: Any) -> str:
    return normalize_text(value)


def _is_finalized(value: Any) -> bool:
    state = _norm(value)
    return state.startswith("FINALIZ") or state in {"CERRADO", "CERRADA", "EJECUTADO", "EJECUTADA"}


def _calendar_indexes(content: bytes) -> dict[str, Any]:
    rows = _parse_monthly(content)
    exact: dict[tuple[str, ...], list[str]] = defaultdict(list)
    relaxed: dict[tuple[str, ...], list[str]] = defaultdict(list)
    by_order: dict[str, list[str]] = defaultdict(list)
    without_order: dict[tuple[str, ...], list[str]] = defaultdict(list)

    for row in rows:
        ot = _norm(row.get("numero_ot_raw"))
        asset = _norm(row.get("activo_codigo"))
        plan = _norm(row.get("plan_clave_software"))
        title = _norm(row.get("titulo"))
        schedule = _norm(row.get("cronograma_planeacion"))
        state = _norm(row.get("estado")) or "SIN ESTADO"
        exact[(ot, asset, plan, title, schedule)].append(state)
        relaxed[(ot, asset, plan)].append(state)
        if ot and ot != "SIN ASIGNAR":
            by_order[ot].append(state)
        else:
            without_order[(asset, plan, title, schedule)].append(state)

    return {
        "rows": rows,
        "exact": exact,
        "relaxed": relaxed,
        "by_order": by_order,
        "without_order": without_order,
    }


def _single_state(values: list[str] | None) -> str | None:
    if not values:
        return None
    unique = [x for x in dict.fromkeys(_norm(v) for v in values) if x]
    if len(unique) == 1:
        return unique[0]
    finalized = [x for x in unique if _is_finalized(x)]
    non_finalized = [x for x in unique if not _is_finalized(x)]
    if finalized and not non_finalized:
        return finalized[0]
    return None


def _resolve_state(row: dict[str, Any], indexes: dict[str, Any]) -> tuple[str | None, str]:
    ot = _norm(row.get("numero_ot"))
    asset = _norm(row.get("activo_codigo"))
    plan = _norm(row.get("plan_clave_software"))
    title = _norm(row.get("titulo"))
    schedule = _norm(row.get("cronograma_planeacion"))

    state = _single_state(indexes["exact"].get((ot, asset, plan, title, schedule)))
    if state:
        return state, "COINCIDENCIA EXACTA"

    state = _single_state(indexes["relaxed"].get((ot, asset, plan)))
    if state:
        return state, "OT + EQUIPO + PLAN"

    if ot and ot != "SIN ASIGNAR":
        state = _single_state(indexes["by_order"].get(ot))
        if state:
            return state, "OT"
    else:
        state = _single_state(indexes["without_order"].get((asset, plan, title, schedule)))
        if state:
            return state, "EQUIPO + PLAN"

    return None, "NO ENCONTRADA"


def _load_programming(conn, programming_id: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    header = conn.execute(text("""
        SELECT id,semana_inicio,semana_fin,especialidad,estado,hh_disponibles,hh_objetivo,hh_reserva,
               creado_por,creado_en,actualizado_en,cierre_archivo_nombre,cierre_comparado_en,cerrado_en,cerrado_por
        FROM programacion.programacion_semanal_v2
        WHERE id=:id
    """), {"id": programming_id}).mappings().first()
    if not header:
        raise V2CloseError("Programación semanal no encontrada")

    rows = [dict(r) for r in conn.execute(text("""
        SELECT pi.id AS programacion_item_id,pi.orden_mantenimiento_id,pi.hh_programadas,pi.requiere_parada,
               pi.origen,pi.backlog_semana_inicio,pi.backlog_semana_fin,pi.estado_cierre,pi.estado_software_cierre,
               o.numero_ot,o.estado AS estado_actual,o.plan_clave_software,o.titulo,o.cronograma_planeacion,
               a.codigo AS activo_codigo,a.descripcion AS activo_descripcion,a.area_codigo,
               p.plan_trabajo,p.descripcion_grupo
        FROM programacion.programacion_item_v2 pi
        JOIN programacion.orden_mantenimiento o ON o.id=pi.orden_mantenimiento_id
        JOIN programacion.activo a ON a.id=o.activo_id
        LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
        WHERE pi.programacion_id=:id
        ORDER BY a.area_codigo,o.numero_ot NULLS LAST,a.codigo,p.plan_trabajo
    """), {"id": programming_id}).mappings()]
    return dict(header), rows


def _compare(conn, programming_id: int, content: bytes) -> dict[str, Any]:
    indexes = _calendar_indexes(content)
    header, rows = _load_programming(conn, programming_id)
    if not rows:
        raise V2CloseError("La programación seleccionada no tiene actividades")

    result_rows: list[dict[str, Any]] = []
    finalized = pending = unmatched = matched = 0
    hh_finalized = hh_pending = 0.0

    for row in rows:
        state, match_type = _resolve_state(row, indexes)
        found = state is not None
        is_final = found and _is_finalized(state)
        if found:
            matched += 1
        if is_final:
            result = "FINALIZADA"
            finalized += 1
            hh_finalized += float(row.get("hh_programadas") or 0)
        elif found:
            result = "PENDIENTE"
            pending += 1
            hh_pending += float(row.get("hh_programadas") or 0)
        else:
            result = "NO_ENCONTRADA"
            unmatched += 1
            hh_pending += float(row.get("hh_programadas") or 0)

        result_rows.append({
            **row,
            "estado_calendario": state or "NO ENCONTRADA EN EL ARCHIVO",
            "resultado_cierre": result,
            "tipo_coincidencia": match_type,
        })

    total = len(result_rows)
    return {
        "programming": header,
        "calendar_rows": len(indexes["rows"]),
        "summary": {
            "programadas": total,
            "encontradas": matched,
            "finalizadas": finalized,
            "pendientes": pending,
            "no_encontradas": unmatched,
            "cumplimiento_pct": round(finalized / total * 100, 1) if total else 0,
            "hh_finalizadas": round(hh_finalized, 2),
            "hh_pendientes": round(hh_pending, 2),
        },
        "rows": result_rows,
    }


def preview_week_close(*, programming_id: int, calendar_content: bytes) -> dict[str, Any]:
    with get_engine().connect() as conn:
        return _compare(conn, programming_id, calendar_content)


def confirm_week_close(
    *,
    programming_id: int,
    calendar_content: bytes,
    filename: str | None = None,
    closed_by: str | None = None,
) -> dict[str, Any]:
    with get_engine().begin() as conn:
        result = _compare(conn, programming_id, calendar_content)
        header = result["programming"]

        for row in result["rows"]:
            item_id = int(row["programacion_item_id"])
            order_id = int(row["orden_mantenimiento_id"])
            status = row["estado_calendario"]
            close_result = row["resultado_cierre"]

            conn.execute(text("""
                UPDATE programacion.programacion_item_v2
                SET estado_cierre=:close_result,
                    estado_software_cierre=:software_state,
                    verificado_cierre_en=now()
                WHERE id=:item_id
            """), {
                "close_result": close_result,
                "software_state": status,
                "item_id": item_id,
            })

            if close_result != "NO_ENCONTRADA":
                conn.execute(text("""
                    UPDATE programacion.orden_mantenimiento
                    SET estado=:state,actualizado_en=now()
                    WHERE id=:order_id
                """), {"state": status, "order_id": order_id})

            if close_result == "FINALIZADA":
                conn.execute(text("DELETE FROM programacion.backlog_v2 WHERE orden_mantenimiento_id=:order_id"), {"order_id": order_id})
            else:
                conn.execute(text("""
                    INSERT INTO programacion.backlog_v2(
                      orden_mantenimiento_id,programacion_origen_id,semana_origen_inicio,semana_origen_fin,
                      especialidad,motivo,movido_por,movido_en,actualizado_en
                    ) VALUES(
                      :order_id,:programming_id,:week_from,:week_to,:specialty,
                      :reason,:closed_by,now(),now()
                    )
                    ON CONFLICT(orden_mantenimiento_id)
                    DO UPDATE SET programacion_origen_id=EXCLUDED.programacion_origen_id,
                      semana_origen_inicio=EXCLUDED.semana_origen_inicio,
                      semana_origen_fin=EXCLUDED.semana_origen_fin,
                      especialidad=EXCLUDED.especialidad,motivo=EXCLUDED.motivo,
                      movido_por=EXCLUDED.movido_por,movido_en=now(),actualizado_en=now()
                """), {
                    "order_id": order_id,
                    "programming_id": programming_id,
                    "week_from": header["semana_inicio"],
                    "week_to": header["semana_fin"],
                    "specialty": header["especialidad"],
                    "reason": "PENDIENTE AL CIERRE SEMANAL" if close_result == "PENDIENTE" else "NO ENCONTRADA EN CALENDARIO DE CIERRE",
                    "closed_by": closed_by,
                })

        conn.execute(text("""
            UPDATE programacion.programacion_semanal_v2
            SET estado='CERRADA',
                cierre_archivo_nombre=:filename,
                cierre_comparado_en=now(),
                cerrado_en=now(),
                cerrado_por=:closed_by,
                actualizado_en=now()
            WHERE id=:id
        """), {"filename": filename, "closed_by": closed_by, "id": programming_id})

        result["programming"]["estado"] = "CERRADA"
        result["programming"]["cierre_archivo_nombre"] = filename
        result["closed"] = True
        result["backlog_generado"] = result["summary"]["pendientes"] + result["summary"]["no_encontradas"]
        return result
