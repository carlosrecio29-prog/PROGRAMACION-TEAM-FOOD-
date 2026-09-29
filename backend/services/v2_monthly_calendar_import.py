from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import re
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.parsers.common import is_operation_plan, normalize_text
from backend.services.v2_import_service import _order_source_key, _parse_monthly, _scalar


def _group_and_label(plan_key: Any) -> tuple[str, str]:
    value = normalize_text(plan_key)
    match = re.match(r"^([^\-–—:]+?)\s*[\-–—:]\s*(.+)$", value)
    if not match:
        return "", value
    return normalize_text(match.group(1)), normalize_text(match.group(2))


def _build_plan_lookups(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]]]:
    by_primary: dict[str, dict[str, Any]] = {}
    by_description: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_primary[normalize_text(f"{row['grupo']}-{row['plan_trabajo']}")] = row
        description = normalize_text(row.get("descripcion_plan_trabajo"))
        if description:
            by_description[(normalize_text(row["grupo"]), description)].append(row)
    return by_primary, by_description


def _resolve_plan(
    plan_key: Any,
    by_primary: dict[str, dict[str, Any]],
    by_description: dict[tuple[str, str], list[dict[str, Any]]],
) -> tuple[dict[str, Any] | None, str]:
    normalized = normalize_text(plan_key)
    direct = by_primary.get(normalized)
    if direct is not None:
        return direct, "PLAN_TRABAJO"

    group, label = _group_and_label(plan_key)
    candidates = by_description.get((group, label), [])
    if len(candidates) == 1:
        return candidates[0], "DESCRIPCION_EXACTA"
    if len(candidates) > 1:
        return None, "DESCRIPCION_AMBIGUA"
    return None, "SIN_COINCIDENCIA"


def import_monthly_calendar(*, monthly_content: bytes, year: int, month: int) -> dict[str, Any]:
    """Conciliación mensual NO destructiva: el maestro decide qué órdenes son OPERACIÓN."""
    if not 1 <= month <= 12 or not 2020 <= year <= 2100:
        raise ValueError("Período inválido")
    monthly = _parse_monthly(monthly_content)
    if not monthly:
        raise ValueError("La Lista de Calendario no contiene registros PMP válidos")
    period = date(year, month, 1)
    warnings: list[str] = []

    with get_engine().begin() as conn:
        programmed_count = conn.execute(text("""
            SELECT count(*)
            FROM programacion.programacion_item_v2 pi
            JOIN programacion.orden_mantenimiento o ON o.id=pi.orden_mantenimiento_id
            WHERE o.periodo=:period
        """), {"period": period}).scalar_one()
        if programmed_count:
            raise ValueError(
                "Ya existen OT de este mes en programación semanal. "
                "No vuelvas a importar el calendario inicial: "
                "usa Cierre semanal para las listas posteriores y conserva el historial."
            )
        previous_keys = set(conn.execute(text("""
            SELECT o.source_key
            FROM programacion.orden_mantenimiento o
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.periodo=:period AND COALESCE(p.es_operacion,false)=false
        """), {"period": period}).scalars().all())
        plan_rows = [
            dict(p)
            for p in conn.execute(text("""
                SELECT id,grupo,plan_trabajo,descripcion_plan_trabajo,es_operacion
                FROM programacion.plan_trabajo
            """)).mappings()
        ]
        plans, plans_by_description = _build_plan_lookups(plan_rows)
        assets = {
            normalize_text(r["codigo"]): int(r["id"])
            for r in conn.execute(text("SELECT id,codigo FROM programacion.activo")).mappings()
        }
        planning_lookup: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for r in conn.execute(text("""
            SELECT p.id,p.plan_clave_software,p.descripcion,p.habilitado,a.codigo AS activo_codigo
            FROM programacion.planeacion p
            JOIN programacion.activo a ON a.id=p.activo_id
        """)).mappings():
            planning_lookup[(
                normalize_text(r["activo_codigo"]),
                normalize_text(r["plan_clave_software"]),
            )].append(dict(r))

        occurrence: Counter[str] = Counter()
        inserted: list[dict[str, Any]] = []
        excluded = 0
        excluded_by_plan: Counter[tuple[str, str, int | None]] = Counter()
        excluded_detail: list[dict[str, Any]] = []
        missing_plan = 0
        missing_asset = 0
        ambiguous_planning = 0
        matched_by_description = 0
        ambiguous_description = 0
        open_in_file = 0
        finalized_in_file = 0
        for row in monthly:
            raw_plan_key = row["plan_clave_software"]
            plan_key = normalize_text(raw_plan_key)
            plan, match_type = _resolve_plan(raw_plan_key, plans, plans_by_description)

            # OPERACIÓN se excluye por la etiqueta del propio archivo o por la
            # clasificación del maestro. Cada exclusión queda resumida por
            # período + plan + especialidad para poder auditarla desde la app.
            if is_operation_plan(raw_plan_key) or (plan is not None and plan["es_operacion"]):
                excluded += 1
                specialty = normalize_text(row.get("especialidad")) or "SIN DEFINIR"
                plan_id = int(plan["id"]) if plan else None
                excluded_by_plan[
                    (_scalar(raw_plan_key), specialty, plan_id)
                ] += 1
                ot_raw = normalize_text(row.get("numero_ot_raw"))
                excluded_detail.append({
                    "periodo": period,
                    "fila_origen": int(row["fila_origen"]),
                    "numero_ot": None if ot_raw in {"", "SIN ASIGNAR"} else _scalar(row.get("numero_ot_raw")),
                    "activo_codigo": _scalar(row.get("activo_codigo")),
                    "plan_clave_software": _scalar(raw_plan_key),
                    "titulo": row.get("titulo"),
                    "especialidad": specialty,
                    "estado": normalize_text(row.get("estado")) or None,
                    "cronograma_planeacion": row.get("cronograma_planeacion"),
                    "tiempo_planeado_min": row.get("tiempo_planeado_min"),
                    "plan_trabajo_id": plan_id,
                })
                continue

            if match_type == "DESCRIPCION_EXACTA":
                matched_by_description += 1
            elif match_type == "DESCRIPCION_AMBIGUA":
                ambiguous_description += 1

            asset_id = assets.get(normalize_text(row["activo_codigo"]))
            if asset_id is None:
                missing_asset += 1
                if len(warnings) < 30:
                    warnings.append(
                        f"Fila {row['fila_origen']}: activo {row['activo_codigo']} no encontrado"
                    )
                continue
            if plan is None:
                missing_plan += 1
                if len(warnings) < 30:
                    detail = (
                        "descripción ambigua en el maestro"
                        if match_type == "DESCRIPCION_AMBIGUA"
                        else "sin coincidencia exacta en PlanTrabajo o DescripcionPlanTrabaj"
                    )
                    warnings.append(
                        f"Fila {row['fila_origen']}: plan {row['plan_clave_software']} {detail}"
                    )

            candidates = planning_lookup.get((
                normalize_text(row["activo_codigo"]), plan_key,
            ), [])
            enabled = [candidate for candidate in candidates if candidate["habilitado"]]
            candidates = enabled or candidates
            if row.get("cronograma_planeacion"):
                exact = [
                    candidate for candidate in candidates
                    if normalize_text(candidate.get("descripcion"))
                    == normalize_text(row["cronograma_planeacion"])
                ]
                if exact:
                    candidates = exact
            if len(candidates) > 1:
                ambiguous_planning += 1
            planning_id = min((int(c["id"]) for c in candidates), default=None)

            ot_raw = normalize_text(row["numero_ot_raw"])
            numero_ot = None if ot_raw in {"", "SIN ASIGNAR"} else _scalar(row["numero_ot_raw"])
            identity_base = (
                "|".join([str(period), "OT", numero_ot]) if numero_ot else
                "|".join([
                    str(period), "SIN ASIGNAR",
                    normalize_text(row["activo_codigo"]), plan_key,
                    normalize_text(row.get("cronograma_planeacion")),
                ])
            )
            occurrence[identity_base] += 1
            state = normalize_text(row.get("estado"))
            if state == "ABIERTO":
                open_in_file += 1
            elif state.startswith("FINALIZ") or state in {"CERRADO", "CERRADA", "COMPLETADO", "COMPLETADA"}:
                finalized_in_file += 1
            inserted.append({
                **row,
                "source_key": _order_source_key(period, row, occurrence[identity_base]),
                "periodo": period,
                "numero_ot": numero_ot,
                "activo_id": asset_id,
                "planeacion_id": planning_id,
                "plan_trabajo_id": int(plan["id"]) if plan else None,
            })

        conn.execute(text("""
            DELETE FROM programacion.operacion_exclusion_detalle_v2
            WHERE periodo=:period
        """), {"period": period})
        if excluded_detail:
            conn.execute(text("""
                INSERT INTO programacion.operacion_exclusion_detalle_v2(
                    periodo,fila_origen,numero_ot,activo_codigo,plan_clave_software,
                    titulo,especialidad,estado,cronograma_planeacion,tiempo_planeado_min,
                    plan_trabajo_id,motivo,origen,registrado_en
                ) VALUES(
                    :periodo,:fila_origen,:numero_ot,:activo_codigo,:plan_clave_software,
                    :titulo,:especialidad,:estado,:cronograma_planeacion,:tiempo_planeado_min,
                    :plan_trabajo_id,'OPERACION','IMPORTACION_CALENDARIO',now()
                )
            """), excluded_detail)

        conn.execute(text("""
            DELETE FROM programacion.operacion_exclusion_periodo_v2
            WHERE periodo=:period
        """), {"period": period})
        if excluded_by_plan:
            exclusion_rows = [
                {
                    "periodo": period,
                    "plan_clave_software": plan_key_raw,
                    "especialidad": specialty,
                    "plan_trabajo_id": plan_id,
                    "cantidad": count,
                }
                for (plan_key_raw, specialty, plan_id), count in excluded_by_plan.items()
            ]
            conn.execute(text("""
                INSERT INTO programacion.operacion_exclusion_periodo_v2(
                    periodo,plan_clave_software,especialidad,plan_trabajo_id,
                    cantidad,motivo,origen,actualizado_en
                ) VALUES(
                    :periodo,:plan_clave_software,:especialidad,:plan_trabajo_id,
                    :cantidad,'OPERACION','IMPORTACION_CALENDARIO',now()
                )
                ON CONFLICT(periodo,plan_clave_software,especialidad) DO UPDATE SET
                    plan_trabajo_id=EXCLUDED.plan_trabajo_id,
                    cantidad=EXCLUDED.cantidad,
                    motivo=EXCLUDED.motivo,
                    origen=EXCLUDED.origen,
                    actualizado_en=now()
            """), exclusion_rows)

        previous_not_in_file = len(previous_keys - {r["source_key"] for r in inserted})
        if previous_not_in_file:
            warnings.append(
                f"{previous_not_in_file} órdenes anteriores de mantenimiento no aparecen "
                "en este archivo; se conservan y requieren conciliación antes de dar "
                "por limpia la cartera inicial."
            )
        if inserted:
            conn.execute(text("""
                INSERT INTO programacion.orden_mantenimiento(
                    source_key,periodo,numero_ot,activo_id,planeacion_id,plan_trabajo_id,
                    plan_clave_software,titulo,especialidad,orden_tipo,responsable,
                    cronograma_planeacion,tiempo_planeado_min,estado,fila_origen
                ) VALUES (
                    :source_key,:periodo,:numero_ot,:activo_id,:planeacion_id,:plan_trabajo_id,
                    :plan_clave_software,:titulo,:especialidad,:orden_tipo,:responsable,
                    :cronograma_planeacion,:tiempo_planeado_min,:estado,:fila_origen
                )
                ON CONFLICT(source_key) DO UPDATE SET
                    titulo=EXCLUDED.titulo,
                    responsable=EXCLUDED.responsable,
                    tiempo_planeado_min=EXCLUDED.tiempo_planeado_min,
                    estado=EXCLUDED.estado,
                    planeacion_id=EXCLUDED.planeacion_id,
                    plan_trabajo_id=EXCLUDED.plan_trabajo_id,
                    actualizado_en=now()
            """), inserted)

        existing = conn.execute(text("""
            SELECT
                count(*) FILTER (WHERE COALESCE(p.es_operacion,false)=false)
                    AS registros_mantenimiento_periodo,
                count(*) FILTER (WHERE COALESCE(p.es_operacion,false)=true)
                    AS registros_operacion_historicos,
                count(*) FILTER (WHERE COALESCE(p.es_operacion,false)=false AND o.estado='ABIERTO')
                    AS registros_mantenimiento_abiertos,
                count(*) FILTER (WHERE COALESCE(p.es_operacion,false)=false AND upper(COALESCE(o.estado,'')) LIKE 'FINALIZ%')
                    AS registros_mantenimiento_finalizados
            FROM programacion.orden_mantenimiento o
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.periodo=:period
        """), {"period": period}).mappings().one()

    return {
        "ok": True,
        "periodo": str(period),
        "pmp_archivo": len(monthly),
        "pmp_excluidos_operacion": excluded,
        "pmp_excluidos_detalle": len(excluded_detail),
        "pmp_importados_o_actualizados": len(inserted),
        "pmp_abiertos_archivo": open_in_file,
        "pmp_finalizados_archivo": finalized_in_file,
        "registros_previos_no_en_archivo": previous_not_in_file,
        "pmp_omitidos_por_activo_faltante": missing_asset,
        "ordenes_sin_plan_maestro": missing_plan,
        "planes_enlazados_por_descripcion_exacta": matched_by_description,
        "planes_con_descripcion_ambigua": ambiguous_description,
        "registros_pmp_con_planeacion_ambigua": ambiguous_planning,
        **dict(existing),
        "warnings": warnings,
    }
