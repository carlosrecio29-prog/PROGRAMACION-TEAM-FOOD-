from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.parsers.common import cell_by_header, header_mapping, normalize_text, workbook_from_bytes


class V2ClosureError(ValueError):
    pass


def _scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _parse_calendar(content: bytes) -> list[dict[str, str]]:
    wb = workbook_from_bytes(content)
    ws = wb.worksheets[0]
    mapping = header_mapping(ws, 1)
    rows: list[dict[str, str]] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        numero_ot = _scalar(cell_by_header(row, mapping, "Orden", "OT", "Orden de Trabajo"))
        activo = _scalar(cell_by_header(row, mapping, "Activo", "Equipo"))
        plan = _scalar(cell_by_header(row, mapping, "PlanTrabajo", "Plan de Trabajo"))
        estado = _scalar(cell_by_header(row, mapping, "Estado"))
        if not numero_ot and not activo and not plan:
            continue
        rows.append({
            "numero_ot": numero_ot,
            "activo": activo,
            "plan": plan,
            "estado": estado,
        })
    if not rows:
        raise V2ClosureError("El archivo no contiene registros de calendario/PMP reconocibles")
    return rows


def _is_finalized(value: str) -> bool:
    state = normalize_text(value)
    return state.startswith("FINALIZ") or state in {"CERRADO", "CERRADA", "COMPLETADO", "COMPLETADA"}


def get_week_closure(programming_id: int) -> dict[str, Any]:
    with get_engine().connect() as conn:
        header = conn.execute(text("""
            SELECT id,semana_inicio,semana_fin,especialidad,estado,cierre_en,cierre_por,cierre_archivo,
                   cierre_total,cierre_finalizadas,cierre_pendientes,cierre_no_encontradas
            FROM programacion.programacion_semanal_v2
            WHERE id=:id
        """), {"id": programming_id}).mappings().first()
        if not header:
            raise V2ClosureError("Programación semanal no encontrada")
        rows = [dict(r) for r in conn.execute(text("""
            SELECT pi.id AS programacion_item_id,pi.orden_mantenimiento_id,pi.hh_programadas,
                   pi.origen_backlog,pi.estado_cierre,pi.finalizado,pi.verificado_en,
                   o.numero_ot,o.estado AS estado_actual,a.codigo AS activo_codigo,
                   a.descripcion AS activo_descripcion,a.area_codigo,
                   p.plan_trabajo,p.descripcion_grupo
            FROM programacion.programacion_item_v2 pi
            JOIN programacion.orden_mantenimiento o ON o.id=pi.orden_mantenimiento_id
            JOIN programacion.activo a ON a.id=o.activo_id
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE pi.programacion_id=:id
            ORDER BY pi.finalizado DESC NULLS LAST,a.area_codigo,o.numero_ot NULLS LAST,a.codigo,p.plan_trabajo
        """), {"id": programming_id}).mappings()]
    verified_rows = [row for row in rows if row.get("estado_cierre")]
    hh_programmed = round(sum(float(row.get("hh_programadas") or 0) for row in rows), 2)
    hh_finalized = round(sum(
        float(row.get("hh_programadas") or 0)
        for row in verified_rows if row.get("finalizado") is True
    ), 2)
    hh_pending = round(sum(
        float(row.get("hh_programadas") or 0)
        for row in verified_rows if row.get("finalizado") is not True
    ), 2)
    finalized = sum(1 for row in verified_rows if row.get("finalizado") is True)
    pending = sum(1 for row in verified_rows if row.get("finalizado") is False)
    not_found = sum(1 for row in verified_rows if row.get("finalizado") is None)
    return {
        "programming": dict(header),
        "rows": rows,
        "summary": {
            "verified": bool(rows) and len(verified_rows) == len(rows),
            "programmed": len(rows),
            "finalized": finalized,
            "pending": pending,
            "not_found": not_found,
            "unchecked": len(rows) - len(verified_rows),
            "hh_programmed": hh_programmed,
            "hh_finalized": hh_finalized,
            "hh_pending": hh_pending,
            "compliance_pct": round(hh_finalized / hh_programmed * 100, 1) if hh_programmed else 0,
        },
    }


def close_week_from_calendar(
    *,
    programming_id: int,
    content: bytes,
    filename: str,
    closed_by: str | None = None,
) -> dict[str, Any]:
    calendar_rows = _parse_calendar(content)

    exact: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    by_ot: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in calendar_rows:
        ot = normalize_text(row["numero_ot"])
        asset = normalize_text(row["activo"])
        plan = normalize_text(row["plan"])
        if ot:
            by_ot[ot].append(row)
        if ot and asset and plan:
            exact[(ot, asset, plan)].append(row)

    with get_engine().begin() as conn:
        programming = conn.execute(text("""
            SELECT id,semana_inicio,semana_fin,especialidad
            FROM programacion.programacion_semanal_v2
            WHERE id=:id
            FOR UPDATE
        """), {"id": programming_id}).mappings().first()
        if not programming:
            raise V2ClosureError("Programación semanal no encontrada")

        items = [dict(r) for r in conn.execute(text("""
            SELECT pi.id AS item_id,pi.orden_mantenimiento_id,o.numero_ot,
                   a.codigo AS activo_codigo,o.plan_clave_software
            FROM programacion.programacion_item_v2 pi
            JOIN programacion.orden_mantenimiento o ON o.id=pi.orden_mantenimiento_id
            JOIN programacion.activo a ON a.id=o.activo_id
            WHERE pi.programacion_id=:id
            ORDER BY pi.id
        """), {"id": programming_id}).mappings()]
        if not items:
            raise V2ClosureError("La programación seleccionada no tiene OT para cerrar")

        finalized_ids: list[int] = []
        pending_ids: list[int] = []
        not_found_ids: list[int] = []

        for item in items:
            ot = normalize_text(item.get("numero_ot"))
            asset = normalize_text(item.get("activo_codigo"))
            plan = normalize_text(item.get("plan_clave_software"))
            matched: dict[str, str] | None = None

            exact_matches = exact.get((ot, asset, plan), []) if ot else []
            if len(exact_matches) == 1:
                matched = exact_matches[0]
            elif ot and len(by_ot.get(ot, [])) == 1:
                matched = by_ot[ot][0]

            if matched is None:
                conn.execute(text("""
                    UPDATE programacion.programacion_item_v2
                    SET estado_cierre='NO ENCONTRADA EN ARCHIVO',finalizado=NULL,
                        verificado_en=now(),cierre_fuente=:filename
                    WHERE id=:item_id
                """), {"filename": filename, "item_id": item["item_id"]})
                not_found_ids.append(int(item["orden_mantenimiento_id"]))
                continue

            state = normalize_text(matched.get("estado")) or "SIN ESTADO"
            finalized = _is_finalized(state)
            conn.execute(text("""
                UPDATE programacion.programacion_item_v2
                SET estado_cierre=:state,finalizado=:finalized,verificado_en=now(),cierre_fuente=:filename
                WHERE id=:item_id
            """), {"state": state, "finalized": finalized, "filename": filename, "item_id": item["item_id"]})
            conn.execute(text("""
                UPDATE programacion.orden_mantenimiento
                SET estado=:state,actualizado_en=now()
                WHERE id=:order_id
            """), {"state": state, "order_id": item["orden_mantenimiento_id"]})
            if finalized:
                finalized_ids.append(int(item["orden_mantenimiento_id"]))
            else:
                pending_ids.append(int(item["orden_mantenimiento_id"]))

        carry_ids = list(dict.fromkeys(pending_ids + not_found_ids))
        if carry_ids:
            conn.execute(text("""
                INSERT INTO programacion.backlog_v2(
                  orden_mantenimiento_id,programacion_origen_id,semana_origen_inicio,semana_origen_fin,
                  especialidad,motivo,movido_por,movido_en,actualizado_en
                )
                SELECT x,:programming_id,:week_start,:week_end,:specialty,
                       'PENDIENTE DE CIERRE SEMANAL',:closed_by,now(),now()
                FROM unnest(CAST(:ids AS bigint[])) AS x
                ON CONFLICT(orden_mantenimiento_id)
                DO UPDATE SET estado_seguimiento='PENDIENTE_DISPONIBLE',
                  programacion_origen_id=EXCLUDED.programacion_origen_id,
                  especialidad=EXCLUDED.especialidad,motivo=EXCLUDED.motivo,movido_por=EXCLUDED.movido_por,
                  ultimo_resultado_cierre='PENDIENTE',ultimo_cierre_en=now(),
                  ultimo_cierre_en=now(),
                  movido_en=now(),actualizado_en=now(),ultima_programacion_id=NULL
            """), {
                "programming_id": programming_id,
                "week_start": programming["semana_inicio"],
                "week_end": programming["semana_fin"],
                "specialty": programming["especialidad"],
                "closed_by": closed_by,
                "ids": carry_ids,
            })
            if not_found_ids:
                conn.execute(text("""
                    UPDATE programacion.backlog_v2
                    SET ultimo_resultado_cierre='NO_ENCONTRADA',
                        motivo='NO ENCONTRADA EN CALENDARIO DE CIERRE',
                        actualizado_en=now()
                    WHERE orden_mantenimiento_id=ANY(CAST(:ids AS bigint[]))
                """), {"ids": not_found_ids})
        if carry_ids:
            conn.execute(text("""
                UPDATE programacion.backlog_v2
                SET primera_semana_origen_inicio=COALESCE(primera_semana_origen_inicio,semana_origen_inicio),
                    primera_semana_origen_fin=COALESCE(primera_semana_origen_fin,semana_origen_fin)
                WHERE orden_mantenimiento_id=ANY(CAST(:ids AS bigint[]))
            """), {"ids": carry_ids})
        if finalized_ids:
            conn.execute(text("""
                UPDATE programacion.backlog_v2
                SET estado_seguimiento='FINALIZADA',ultimo_resultado_cierre='FINALIZADA',
                    ultimo_cierre_en=now(),finalizado_en=now(),finalizado_por=:closed_by,
                    ultima_programacion_id=NULL,actualizado_en=now()
                WHERE orden_mantenimiento_id=ANY(CAST(:ids AS bigint[]))
            """), {"ids": finalized_ids, "closed_by": closed_by})

        conn.execute(text("""
            UPDATE programacion.programacion_semanal_v2
            SET estado='CERRADA',cierre_en=now(),cierre_por=:closed_by,cierre_archivo=:filename,
                cierre_total=:total,cierre_finalizadas=:finalized,cierre_pendientes=:pending,
                cierre_no_encontradas=:not_found,actualizado_en=now()
            WHERE id=:id
        """), {
            "closed_by": closed_by,
            "filename": filename,
            "total": len(items),
            "finalized": len(finalized_ids),
            "pending": len(pending_ids),
            "not_found": len(not_found_ids),
            "id": programming_id,
        })

    result = get_week_closure(programming_id)
    result["summary"]["moved_to_backlog"] = len(carry_ids)
    return result
