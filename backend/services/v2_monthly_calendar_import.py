from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.parsers.common import normalize_text
from backend.services.v2_import_service import _order_source_key, _parse_monthly, _scalar


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
        plans = {
            normalize_text(f"{p['grupo']}-{p['plan_trabajo']}"): p
            for p in conn.execute(text(
                "SELECT id,grupo,plan_trabajo,es_operacion FROM programacion.plan_trabajo"
            )).mappings()
        }
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
        missing_plan = 0
        missing_asset = 0
        ambiguous_planning = 0
        for row in monthly:
            plan_key = normalize_text(row["plan_clave_software"])
            plan = plans.get(plan_key)
            if plan is not None and plan["es_operacion"]:
                excluded += 1
                continue

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
                    warnings.append(
                        f"Fila {row['fila_origen']}: plan {row['plan_clave_software']} no encontrado"
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
            inserted.append({
                **row,
                "source_key": _order_source_key(period, row, occurrence[identity_base]),
                "periodo": period,
                "numero_ot": numero_ot,
                "activo_id": asset_id,
                "planeacion_id": planning_id,
                "plan_trabajo_id": int(plan["id"]) if plan else None,
            })

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
                    AS registros_operacion_historicos
            FROM programacion.orden_mantenimiento o
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.periodo=:period
        """), {"period": period}).mappings().one()

    return {
        "ok": True,
        "periodo": str(period),
        "pmp_archivo": len(monthly),
        "pmp_excluidos_operacion": excluded,
        "pmp_importados_o_actualizados": len(inserted),
        "pmp_omitidos_por_activo_faltante": missing_asset,
        "ordenes_sin_plan_maestro": missing_plan,
        "registros_pmp_con_planeacion_ambigua": ambiguous_planning,
        **dict(existing),
        "warnings": warnings,
    }
