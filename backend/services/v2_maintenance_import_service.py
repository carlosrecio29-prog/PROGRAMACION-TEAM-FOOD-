from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.parsers.common import cell_by_header, header_mapping, normalize_text, workbook_from_bytes
from backend.services.v2_import_service import (
    _number,
    _order_source_key,
    _parse_monthly,
    _parse_plans,
    _plan_key,
    _scalar,
)


def _parse_activities(content: bytes) -> tuple[list[dict[str, Any]], int]:
    wb = workbook_from_bytes(content)
    ws = wb.worksheets[0]
    mapping = header_mapping(ws, 1)
    by_key: dict[tuple[str, int], dict[str, Any]] = {}
    duplicates = 0

    for row_number, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        group = _scalar(cell_by_header(row, mapping, "Grupo"))
        plan = _scalar(cell_by_header(row, mapping, "PlanTrabajo", "Plan de Trabajo"))
        activity = _scalar(cell_by_header(row, mapping, "Actividad"))
        consecutive_raw = cell_by_header(row, mapping, "Consecutivo")
        if not group or not plan or not activity or consecutive_raw in (None, ""):
            continue
        try:
            consecutive = int(float(consecutive_raw))
        except (TypeError, ValueError):
            continue

        required_raw = normalize_text(cell_by_header(row, mapping, "Obligatorio"))
        required = None
        if required_raw in {"SI", "SÍ", "TRUE", "1", "X"}:
            required = True
        elif required_raw in {"NO", "FALSE", "0"}:
            required = False

        record = {
            "plan_key": _plan_key(group, plan),
            "consecutivo": consecutive,
            "actividad": activity,
            "tiempo_min": _number(cell_by_header(row, mapping, "Tiempo")),
            "obligatorio": required,
            "fila_origen": row_number,
        }
        key = (record["plan_key"], consecutive)
        if key in by_key:
            duplicates += 1
            continue
        by_key[key] = record

    return list(by_key.values()), duplicates


def import_maintenance_base(
    *,
    plans_content: bytes,
    activities_content: bytes,
    monthly_content: bytes,
    year: int,
    month: int,
) -> dict[str, Any]:
    if not 1 <= month <= 12:
        raise ValueError("Mes inválido")

    plans = _parse_plans(plans_content)
    activities, duplicate_activities = _parse_activities(activities_content)
    monthly = _parse_monthly(monthly_content)
    if not plans:
        raise ValueError("El archivo Plan de Trabajo no contiene registros válidos")
    if not activities:
        raise ValueError("El archivo Plan de Trabajo - Actividades no contiene registros válidos")
    if not monthly:
        raise ValueError("La Lista de Calendario no contiene registros PMP válidos")

    period = date(year, month, 1)
    warnings: list[str] = []

    with get_engine().begin() as conn:
        programmed = conn.execute(text("""
            SELECT count(*)
            FROM programacion.programacion_item_v2 pi
            JOIN programacion.orden_mantenimiento om ON om.id=pi.orden_mantenimiento_id
            WHERE om.periodo=:period
        """), {"period": period}).scalar_one()
        if programmed:
            raise ValueError(
                "Este período ya tiene órdenes guardadas en programación semanal. "
                "No se reemplazó la base para proteger la programación existente."
            )

        conn.execute(text("""INSERT INTO programacion.plan_trabajo(
          grupo,descripcion_grupo,plan_trabajo,descripcion_plan_trabajo,tipo_frecuencia,
          valor_frecuencia,tiempo_ejecucion_min,numero_personas,tiempo_parada_min,
          especialidad,orden_tipo,estado,habilitado,fila_origen
        ) VALUES(
          :grupo,:descripcion_grupo,:plan_trabajo,:descripcion_plan_trabajo,:tipo_frecuencia,
          :valor_frecuencia,:tiempo_ejecucion_min,:numero_personas,:tiempo_parada_min,
          :especialidad,:orden_tipo,:estado,:habilitado,:fila_origen
        )
        ON CONFLICT (grupo,plan_trabajo) DO UPDATE SET
          descripcion_grupo=EXCLUDED.descripcion_grupo,
          descripcion_plan_trabajo=EXCLUDED.descripcion_plan_trabajo,
          tipo_frecuencia=EXCLUDED.tipo_frecuencia,
          valor_frecuencia=EXCLUDED.valor_frecuencia,
          tiempo_ejecucion_min=EXCLUDED.tiempo_ejecucion_min,
          numero_personas=EXCLUDED.numero_personas,
          tiempo_parada_min=EXCLUDED.tiempo_parada_min,
          especialidad=EXCLUDED.especialidad,
          orden_tipo=EXCLUDED.orden_tipo,
          estado=EXCLUDED.estado,
          habilitado=EXCLUDED.habilitado,
          fila_origen=EXCLUDED.fila_origen,
          actualizado_en=now()
        """), plans)

        plan_map = {
            _plan_key(row["grupo"], row["plan_trabajo"]): int(row["id"])
            for row in conn.execute(text(
                "SELECT id,grupo,plan_trabajo FROM programacion.plan_trabajo"
            )).mappings()
        }

        # Reconstituye la relación que quedó en NULL al reemplazar el maestro anterior.
        conn.execute(text("UPDATE programacion.planeacion SET plan_trabajo_id=NULL"))
        planning_links = []
        for row in conn.execute(text(
            "SELECT id,plan_clave_software FROM programacion.planeacion"
        )).mappings():
            plan_id = plan_map.get(normalize_text(row["plan_clave_software"]))
            if plan_id is not None:
                planning_links.append({"id": int(row["id"]), "plan_id": plan_id})
        if planning_links:
            conn.execute(text("""
                UPDATE programacion.planeacion
                SET plan_trabajo_id=:plan_id, actualizado_en=now()
                WHERE id=:id
            """), planning_links)

        # La lista de actividades es un maestro completo: se reemplaza como catálogo.
        conn.execute(text("DELETE FROM programacion.plan_trabajo_actividad"))
        activity_db = []
        missing_activity_plans = 0
        for row in activities:
            plan_id = plan_map.get(row["plan_key"])
            if plan_id is None:
                missing_activity_plans += 1
                continue
            activity_db.append({
                "plan_trabajo_id": plan_id,
                "consecutivo": row["consecutivo"],
                "actividad": row["actividad"],
                "tiempo_min": row["tiempo_min"],
                "obligatorio": row["obligatorio"],
                "fila_origen": row["fila_origen"],
            })
        if activity_db:
            conn.execute(text("""INSERT INTO programacion.plan_trabajo_actividad(
              plan_trabajo_id,consecutivo,actividad,tiempo_min,obligatorio,fila_origen
            ) VALUES(
              :plan_trabajo_id,:consecutivo,:actividad,:tiempo_min,:obligatorio,:fila_origen
            )
            """), activity_db)

        asset_map = {
            normalize_text(row["codigo"]): int(row["id"])
            for row in conn.execute(text("SELECT id,codigo FROM programacion.activo")).mappings()
        }
        planning_lookup: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in conn.execute(text("""SELECT
              p.id,p.plan_clave_software,p.descripcion,p.habilitado,a.codigo activo_codigo
            FROM programacion.planeacion p
            JOIN programacion.activo a ON a.id=p.activo_id
        """)).mappings():
            planning_lookup[(
                normalize_text(row["activo_codigo"]),
                normalize_text(row["plan_clave_software"]),
            )].append(dict(row))

        # Solo se reemplaza el PMP del período seleccionado.
        conn.execute(text(
            "DELETE FROM programacion.orden_mantenimiento WHERE periodo=:period"
        ), {"period": period})

        occurrence: Counter[str] = Counter()
        order_db = []
        missing_assets = 0
        missing_order_plans = 0
        ambiguous_planning = 0
        for row in monthly:
            asset_id = asset_map.get(normalize_text(row["activo_codigo"]))
            if asset_id is None:
                missing_assets += 1
                if len(warnings) < 30:
                    warnings.append(
                        f"PMP fila {row['fila_origen']}: activo {row['activo_codigo']} no encontrado"
                    )
                continue

            plan_id = plan_map.get(normalize_text(row["plan_clave_software"]))
            if plan_id is None:
                missing_order_plans += 1

            candidates = planning_lookup.get((
                normalize_text(row["activo_codigo"]),
                normalize_text(row["plan_clave_software"]),
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
            planning_id = min((int(candidate["id"]) for candidate in candidates), default=None)

            ot_raw = normalize_text(row["numero_ot_raw"])
            numero_ot = None if ot_raw in {"", "SIN ASIGNAR"} else _scalar(row["numero_ot_raw"])
            identity_base = (
                "|".join([str(period), "OT", numero_ot]) if numero_ot else
                "|".join([
                    str(period), "SIN ASIGNAR",
                    normalize_text(row["activo_codigo"]),
                    normalize_text(row["plan_clave_software"]),
                    normalize_text(row.get("cronograma_planeacion")),
                ])
            )
            occurrence[identity_base] += 1
            order_db.append({
                **row,
                "source_key": _order_source_key(period, row, occurrence[identity_base]),
                "periodo": period,
                "numero_ot": numero_ot,
                "activo_id": asset_id,
                "planeacion_id": planning_id,
                "plan_trabajo_id": plan_id,
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
            )
            """), order_db)

        stats = conn.execute(text("""SELECT
          (SELECT count(*) FROM programacion.plan_trabajo) planes,
          (SELECT count(*) FROM programacion.plan_trabajo_actividad) actividades,
          (SELECT count(*) FROM programacion.planeacion WHERE plan_trabajo_id IS NOT NULL) planeaciones_enlazadas,
          (SELECT count(*) FROM programacion.planeacion WHERE plan_trabajo_id IS NULL) planeaciones_sin_enlace,
          (SELECT count(*) FROM programacion.orden_mantenimiento WHERE periodo=:period) registros_pmp,
          (SELECT count(DISTINCT numero_ot) FROM programacion.orden_mantenimiento WHERE periodo=:period AND numero_ot IS NOT NULL) ot_distintas,
          (SELECT count(*) FROM programacion.orden_mantenimiento WHERE periodo=:period AND especialidad='MEC') pmp_mecanica
        """), {"period": period}).mappings().one()

    return {
        "ok": True,
        "periodo": str(period),
        **dict(stats),
        "planes_archivo": len(plans),
        "actividades_archivo": len(activities) + duplicate_activities,
        "actividades_duplicadas_omitidas": duplicate_activities,
        "actividades_sin_plan_maestro": missing_activity_plans,
        "pmp_archivo": len(monthly),
        "pmp_omitidos_por_activo_faltante": missing_assets,
        "ordenes_sin_plan_maestro": missing_order_plans,
        "registros_pmp_con_planeacion_ambigua": ambiguous_planning,
        "warnings": warnings,
    }
