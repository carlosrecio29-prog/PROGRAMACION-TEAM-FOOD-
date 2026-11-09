from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from backend.database import get_engine

SPREADSHEET_ID = "1Or0L7epumDQUsUuLjb4FXt-7FRbC16pJ8-b0VwROwdo"
SHEET_RANGE = "'BASE DE DATOS'!A1:M"
SPECIALTIES = {"ELE", "MEC", "MET", "SER"}
MONTHS = {name: i for i, name in enumerate(
    ("ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
     "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"), 1
)}
REQUIRED_HEADERS = (
    "MES", "# DE ORDEN", "ESPECIALIDAD", "CODIGO",
    "ESTADO", "PLAN DE TRABAJO"
)


class SheetSyncError(Exception):
    pass


def _norm(value: Any) -> str:
    string = unicodedata.normalize("NFD", str(value or ""))
    return re.sub(r"\s+", " ", "".join(ch for ch in string if not unicodedata.combining(ch))).strip().upper()


def _status(value: Any) -> str | None:
    raw = _norm(value)
    if raw.startswith("FINALIZ"): return "FINALIZADA"
    if raw.startswith("ANUL"): return "ANULADA"
    if raw.startswith(("PEND", "ABIER", "PROGRAM", "EN PROCESO")): return "PENDIENTE"
    return None


def _operation(plan: Any) -> bool:
    name = re.sub(r"^\d+\s*[-–—:._/|]+\s*", "", _norm(plan))
    return bool(re.match(r"^OPERACION(?:\b|\s|[-–—:._/|])", name))


def _minutes(value: Any) -> Decimal | None:
    if value is None or not str(value).strip(): return None
    try:
        result = Decimal(str(value).strip().replace(" ", "").replace(",", "."))
        return result if result.is_finite() and result >= 0 else None
    except (ValueError, InvalidOperation):
        return None


def _parse_rows(values: list[list[Any]], period: date) -> tuple[dict[str, dict[str, Any]], list[str], dict[str, int]]:
    if not values: raise SheetSyncError("BASE DE DATOS no contiene encabezados.")
    head = {_norm(name): idx for idx, name in enumerate(values[0])}
    missing = [name for name in REQUIRED_HEADERS if name not in head]
    if missing: raise SheetSyncError("BASE DE DATOS no contiene las columnas requeridas: " + ", ".join(missing))

    def cell(row: list[Any], name: str) -> Any:
        index = head.get(name)
        return row[index] if index is not None and index < len(row) else None

    selected: dict[str, dict[str, Any]] = {}
    conflicts: set[str] = set()
    errors: list[str] = []
    stats: Counter[str] = Counter()
    for row_number, row in enumerate(values[1:], 2):
        if MONTHS.get(_norm(cell(row, "MES"))) != period.month:
            continue
        ot = _norm(cell(row, "# DE ORDEN"))
        if not ot:
            continue
        spec = _norm(cell(row, "ESPECIALIDAD"))
        if spec not in SPECIALTIES:
            continue
        stats["filas_periodo"] += 1
        source_status = _status(cell(row, "ESTADO"))
        plan = str(cell(row, "PLAN DE TRABAJO") or "").strip()
        asset = str(cell(row, "CODIGO") or "").strip()
        if not re.fullmatch(r"OT-[\d]+-[\d]{2,4}", ot):
            errors.append(f"Fila {row_number}: número de OT inválido")
            continue
        if not source_status or not asset or not plan or _norm(plan) == "NO ENCONTRADO":
            errors.append(f"{ot}: estado, equipo o plan incompleto (fila {row_number})")
            continue
        raw_year = str(cell(row, "ANO") or "").strip()
        if raw_year and raw_year.isdigit():
            source_year = int(raw_year)
        else:
            suffix = ot.rsplit("-", 1)[-1]
            source_year = 2000 + int(suffix) if len(suffix) == 2 else int(suffix)
        item = {
            "ot": ot, "spec": spec, "asset": asset, "plan": plan,
            "title": str(cell(row, "OBSERVACION") or cell(row, "DESCRIPCION") or "").strip(),
            "asset_description": str(cell(row, "DESCRIPCION") or "").strip(),
            "criticidad": _norm(cell(row, "CRITICIDAD"))[:1],
            "estado": source_status, "source_year": source_year,
            "minutes": _minutes(cell(row, "TIEMPO")),
            "operation": _operation(plan), "row": row_number,
        }
        previous = selected.get(ot)
        if previous:
            stats["filas_repetidas"] += 1
            if any(previous[field] != item[field] for field in ("spec", "asset", "plan", "estado")):
                conflicts.add(ot)
        else:
            selected[ot] = item
    for ot in conflicts:
        selected.pop(ot, None)
        errors.append(f"{ot}: filas con datos contradictorios; no se actualizará automáticamente")
    stats["ots_unicas_validas"] = len(selected)
    stats["duplicados_conflictivos"] = len(conflicts)
    if not stats["filas_periodo"]:
        raise SheetSyncError(f"No hay OT de {period.month:02d}/{period.year} en BASE DE DATOS; sincronización cancelada.")
    return selected, errors, dict(stats)


def _read_sheet() -> list[list[Any]]:
    raw = os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise SheetSyncError("Falta configurar GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON en Vercel.")
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(raw), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        session = AuthorizedSession(credentials)
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{SHEET_RANGE}"
        response = session.get(url, params={"valueRenderOption": "FORMATTED_VALUE"}, timeout=25)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result.get("values"), list):
            raise ValueError("Respuesta incompleta")
        return result["values"]
    except SheetSyncError:
        raise
    except Exception as exc:
        # No exponer JSON de la cuenta de servicio, tokens ni respuestas privadas.
        raise SheetSyncError(
            "No fue posible leer BASE DE DATOS desde Google Sheets. Comprueba la cuenta de servicio, su acceso como lector y la API de Sheets."
        ) from exc


def _lookup_plan(plans: dict[str, dict[str, Any]], plan: str) -> dict[str, Any] | None:
    return plans.get(_norm(plan))


def _write_change(conn, run_id: int, period: date, item: dict[str, Any], action: str,
                  order_id: int | None = None, before: str | None = None, after: str | None = None,
                  detail: str | None = None) -> None:
    conn.execute(text("""
        INSERT INTO programacion.google_sheet_sync_cambio_v2(
          sincronizacion_id,periodo,numero_ot,orden_mantenimiento_id,accion,
          estado_anterior,estado_nuevo,detalle)
        VALUES (:run,:period,:ot,:order_id,:action,:before,:after,:detail)
    """), {"run": run_id, "period": period, "ot": item["ot"], "order_id": order_id,
           "action": action, "before": before, "after": after, "detail": detail})


def _week_snapshots(conn, period: date, today: date, states: dict[str, dict[str, Any]], trigger: str) -> int:
    weeks = conn.execute(text("""
      SELECT id FROM programacion.programacion_semanal_v2
      WHERE semana_inicio >= :period
        AND semana_inicio < (:period + INTERVAL '1 month')
        AND semana_inicio <= :today AND semana_fin >= :today
        AND estado <> 'CERRADA'
    """), {"period": period, "today": today}).scalars().all()
    saved = 0
    for week_id in weeks:
        items = conn.execute(text("""
          SELECT pi.id AS item_id,pi.orden_mantenimiento_id,pi.hh_programadas,
                 o.numero_ot,a.area_codigo,ra.descripcion AS area_nombre,
                 sm.estado AS manual_status
          FROM programacion.programacion_item_v2 pi
          JOIN programacion.orden_mantenimiento o ON o.id=pi.orden_mantenimiento_id
          JOIN programacion.activo a ON a.id=o.activo_id
          LEFT JOIN programacion.activo ra ON ra.codigo='BA-' || a.area_codigo
          LEFT JOIN programacion.seguimiento_estado_manual_v2 sm ON sm.programacion_item_id=pi.id
          WHERE pi.programacion_id=:week ORDER BY pi.id
        """), {"week": week_id}).mappings().all()
        if not items:
            continue
        latest = conn.execute(text("""
          SELECT id,archivo_nombre FROM programacion.seguimiento_semanal_v2
          WHERE programacion_id=:week ORDER BY registrado_en DESC,id DESC LIMIT 1
        """), {"week": week_id}).mappings().first()
        prev_finished: set[int] = set(conn.execute(text("""
          SELECT DISTINCT si.orden_mantenimiento_id
          FROM programacion.seguimiento_semanal_item_v2 si
          JOIN programacion.seguimiento_semanal_v2 ss ON ss.id=si.seguimiento_id
          WHERE ss.programacion_id=:week AND si.finalizado=true
        """), {"week": week_id}).scalars())
        prepared: list[dict[str, Any]] = []
        for it in items:
            ot = _norm(it["numero_ot"])
            source = states.get(ot)
            status = source["estado"] if source and not source["operation"] else None
            manual = it["manual_status"]
            if manual in ("FINALIZADA", "PENDIENTE", "ANULADA"):
                effective = manual
            elif status == "FINALIZADA" or int(it["orden_mantenimiento_id"]) in prev_finished:
                effective = "FINALIZADA"
            else:
                effective = status
            final = True if effective == "FINALIZADA" else False if effective == "PENDIENTE" else None
            prepared.append({
                "item_id": int(it["item_id"]), "order_id": int(it["orden_mantenimiento_id"]),
                "ot": it["numero_ot"], "area": it["area_codigo"], "area_name": it["area_nombre"],
                "hh": float(it["hh_programadas"] or 0),
                "status": status, "final": final,
                "match": "GOOGLE_SHEETS_BASE_DE_DATOS" if source else "SIN_COINCIDENCIA",
                "annulled": effective == "ANULADA",
            })
        # Evitar fotografías idénticas; conservar la precedencia de estados manuales.
        if latest and str(latest["archivo_nombre"] or "").startswith("GOOGLE_SHEETS_"):
            last_rows = conn.execute(text("""
              SELECT programacion_item_id,estado_calendario,finalizado
              FROM programacion.seguimiento_semanal_item_v2 WHERE seguimiento_id=:id
            """), {"id": latest["id"]}).mappings().all()
            before = {int(x["programacion_item_id"]): (x["estado_calendario"], x["finalizado"]) for x in last_rows}
            if len(before) == len(prepared) and all(
                before.get(x["item_id"]) == (x["status"], x["final"]) for x in prepared
            ):
                continue
        n = len(prepared)
        done = sum(x["final"] is True for x in prepared)
        pending = sum(x["final"] is False for x in prepared)
        ann = sum(x["annulled"] for x in prepared)
        hh_total = sum(x["hh"] for x in prepared)
        hh_done = sum(x["hh"] for x in prepared if x["final"] is True)
        hh_pending = sum(x["hh"] for x in prepared if x["final"] is False)
        hh_ann = sum(x["hh"] for x in prepared if x["annulled"])
        header_id = conn.execute(text("""
          INSERT INTO programacion.seguimiento_semanal_v2(
            programacion_id,archivo_nombre,registrado_por,
            total_items,finalizados,pendientes,sin_coincidencia,
            hh_programadas,hh_finalizadas,hh_pendientes,avance_ot_pct,avance_hh_pct,
            anuladas,hh_anuladas)
          VALUES (:week,'GOOGLE_SHEETS_BASE_DE_DATOS',:actor,
            :total,:done,:pending,:missing,:hh_total,:hh_done,:hh_pending,:pct,:hh_pct,
            :ann,:hh_ann) RETURNING id
        """), {
            "week": week_id, "actor": "SINCRONIZACION_" + trigger,
            "total": n, "done": done, "pending": pending,
            "missing": n - done - pending - ann,
            "hh_total": hh_total, "hh_done": hh_done, "hh_pending": hh_pending,
            "pct": round(100 * done / (n - ann), 1) if n > ann else 0,
            "hh_pct": round(100 * hh_done / (hh_total - hh_ann), 1) if hh_total > hh_ann else 0,
            "ann": ann, "hh_ann": hh_ann,
        }).scalar_one()
        conn.execute(text("""
          INSERT INTO programacion.seguimiento_semanal_item_v2(
            seguimiento_id,programacion_item_id,orden_mantenimiento_id,numero_ot,
            area_codigo,area_nombre,hh_programadas,estado_calendario,finalizado,coincidencia)
          VALUES (:tracking_id,:item_id,:order_id,:ot,
                  :area,:area_name,:hh,:status,:final,:match)
        """), [{**item, "tracking_id": header_id} for item in prepared])
        saved += 1
    return saved


def sync_month(*, year: int, month: int, trigger: str) -> dict[str, Any]:
    if trigger not in ("CRON", "MANUAL") or not (2020 <= year <= 2100 and 1 <= month <= 12):
        raise SheetSyncError("Parámetros de sincronización inválidos.")
    period = date(year, month, 1)
    today = datetime.now(ZoneInfo("America/Bogota")).date()
    if period > today.replace(day=1):
        raise SheetSyncError("No se puede sincronizar un mes futuro.")
    engine = get_engine()
    try:
        values = _read_sheet()
        states, warnings, scan = _parse_rows(values, period)
        if len(states) > 10000:
            raise SheetSyncError("La cantidad de OT supera el límite seguro por mes.")
    except SheetSyncError as exc:
        with engine.begin() as conn:
            conn.execute(text("""
              INSERT INTO programacion.google_sheet_sync_run_v2(
                periodo,origen,estado,error_resumido)
              VALUES (:period,:origin,'ERROR',:detail)
            """), {"period": period, "origin": trigger, "detail": str(exc)[:400]})
        raise
    try:
        with engine.begin() as conn:
            locked = conn.execute(text("SELECT pg_try_advisory_xact_lock(72026,1109)")).scalar_one()
            if not locked:
                return {"ok": False, "estado": "OMITIDA", "mensaje": "Otra sincronización está en curso."}
            run_id = conn.execute(text("""
              INSERT INTO programacion.google_sheet_sync_run_v2(periodo,origen,estado)
              VALUES (:period,:origin,'COMPLETADA') RETURNING id
            """), {"period": period, "origin": trigger}).scalar_one()

            assets = {_norm(r["codigo"]): int(r["id"]) for r in conn.execute(text(
                "SELECT id,codigo FROM programacion.activo"
            )).mappings()}
            plans: dict[str, dict[str, Any]] = {}
            for r in conn.execute(text("""
              SELECT id,grupo,plan_trabajo,descripcion_plan_trabajo,orden_tipo,es_operacion
              FROM programacion.plan_trabajo
            """)).mappings():
                plan = dict(r)
                plans.setdefault(_norm(f"{r['grupo']}-{r['plan_trabajo']}"), plan)
                plans.setdefault(_norm(f"{r['grupo']}-{r['descripcion_plan_trabajo']}"), plan)

            ots = list(states)
            previous: dict[str, list[dict[str, Any]]] = {}
            for r in conn.execute(text("""
              SELECT o.id,o.numero_ot,o.periodo,o.estado,o.especialidad,
                b.id AS backlog_id,b.estado_seguimiento,
                EXISTS(
                  SELECT 1 FROM programacion.programacion_item_v2 pi
                  JOIN programacion.programacion_semanal_v2 ps ON ps.id=pi.programacion_id
                  WHERE pi.orden_mantenimiento_id=o.id AND ps.estado='CERRADA'
                ) AS has_closed,
                EXISTS(SELECT 1 FROM programacion.programacion_item_v2 pi
                       WHERE pi.orden_mantenimiento_id=o.id) AS has_programming
              FROM programacion.orden_mantenimiento o
              LEFT JOIN programacion.backlog_v2 b ON b.orden_mantenimiento_id=o.id
              WHERE upper(btrim(o.numero_ot)) = ANY(CAST(:ots AS text[]))
              ORDER BY o.periodo DESC,o.id DESC
            """), {"ots": ots}).mappings():
                previous.setdefault(_norm(r["numero_ot"]), []).append(dict(r))

            counts: Counter[str] = Counter()
            group_ops: Counter[tuple[str, str]] = Counter()
            prior_end = period - timedelta(days=1)
            prior_snapshots = {
                _norm(r["numero_ot"]): r["estado"]
                for r in conn.execute(text("""
                    SELECT numero_ot,estado FROM programacion.google_sheet_ot_estado_v2
                    WHERE periodo=:period
                """), {"period": period}).mappings()
            }
            existing_operations = {
                _norm(ot) for ot in conn.execute(text("""
                    SELECT numero_ot FROM programacion.operacion_exclusion_detalle_v2
                    WHERE periodo=:period
                """), {"period": period}).scalars()
            }
            observations: list[dict[str, Any]] = []
            source_changes: list[dict[str, Any]] = []
            for ot, item in states.items():
                found = previous.get(ot, [])
                order = next((x for x in found if x["periodo"] == period), None) or (found[0] if found else None)
                plan = _lookup_plan(plans, item["plan"])
                if item["operation"]:
                    counts["operaciones"] += 1
                    group_ops[(item["plan"], item["spec"])] += 1
                    # Excluidas: no crear PMP ni afectar los indicadores de cumplimiento.
                    if ot not in existing_operations:
                        conn.execute(text("""
                          INSERT INTO programacion.operacion_exclusion_detalle_v2(
                            periodo,fila_origen,numero_ot,activo_codigo,plan_clave_software,
                            titulo,especialidad,estado,tiempo_planeado_min,plan_trabajo_id,motivo,origen)
                          VALUES (:period,:row,:ot,:asset,:plan,:title,:spec,:state,:minutes,:plan_id,
                                  'OPERACION','GOOGLE_SHEETS_BASE_SYNC')
                        """), {"period": period, "row": item["row"], "ot": ot, "asset": item["asset"],
                                "plan": item["plan"], "title": item["title"], "spec": item["spec"],
                                "state": item["estado"], "minutes": item["minutes"],
                                "plan_id": plan["id"] if plan else None})
                elif order is None:
                    if item["source_year"] != year:
                        warnings.append(f"{ot}: orden heredada sin registro previo; requiere revisión manual")
                        counts["conflictos"] += 1
                    elif not plan or plan["es_operacion"]:
                        warnings.append(f"{ot}: plan no encontrado o clasificado como OPERACIÓN")
                        counts["conflictos"] += 1
                    else:
                        asset_id = assets.get(_norm(item["asset"]))
                        if asset_id is None and _norm(item["asset"]).startswith("BA-"):
                            asset_id = conn.execute(text("""
                              INSERT INTO programacion.activo(
                                codigo,descripcion,criticidad,especialidad,area_codigo,habilitado,fila_origen)
                              VALUES (:code,:description,:criticality,:spec,:area,true,:row)
                              ON CONFLICT (codigo) DO UPDATE SET codigo=EXCLUDED.codigo
                              RETURNING id
                            """), {
                                "code": item["asset"], "description": item["asset_description"],
                                "criticality": item["criticidad"] if item["criticidad"] in ("A","B","C") else None,
                                "spec": item["spec"], "area": item["asset"].split("-")[1] if "-" in item["asset"] else None,
                                "row": item["row"],
                            }).scalar_one()
                            assets[_norm(item["asset"])] = asset_id
                        if asset_id is None:
                            warnings.append(f"{ot}: código de equipo inválido; requiere revisión")
                            counts["conflictos"] += 1
                        else:
                            key = hashlib.sha256(f"{period.isoformat()}|OT|{ot}|1".encode()).hexdigest()
                            order_id = conn.execute(text("""
                              INSERT INTO programacion.orden_mantenimiento(
                                source_key,periodo,numero_ot,activo_id,plan_trabajo_id,plan_clave_software,
                                titulo,especialidad,orden_tipo,tiempo_planeado_min,estado,fila_origen)
                              VALUES (:key,:period,:ot,:asset_id,:plan_id,:plan,:title,:spec,
                                      :kind,:minutes,:state,:row)
                              ON CONFLICT (source_key) DO NOTHING RETURNING id
                            """), {
                                "key": key, "period": period, "ot": ot, "asset_id": asset_id,
                                "plan_id": plan["id"], "plan": item["plan"], "title": item["title"],
                                "spec": item["spec"], "kind": plan["orden_tipo"] or "PREV",
                                "minutes": item["minutes"], "state": "ABIERTO" if item["estado"] == "PENDIENTE" else item["estado"],
                                "row": item["row"],
                            }).scalar()
                            if order_id:
                                counts["nuevas"] += 1
                                _write_change(conn,run_id,period,item,"NUEVA_OT",int(order_id),after=item["estado"])
                else:
                    if item["spec"] != order["especialidad"]:
                        warnings.append(f"{ot}: especialidad diferente; se conservó el maestro")
                        counts["conflictos"] += 1
                    elif not item["operation"]:
                        if order["periodo"] == period and not order["has_closed"]:
                            old = _status(order["estado"])
                            new = item["estado"]
                            if old in ("FINALIZADA", "ANULADA") and new == "PENDIENTE":
                                counts["conflictos"] += 1
                                warnings.append(f"{ot}: estado retrocedió a PENDIENTE; sin cambios por seguridad")
                            elif old != new:
                                conn.execute(text("""
                                  UPDATE programacion.orden_mantenimiento
                                  SET estado=:state,actualizado_en=now()
                                  WHERE id=:id
                                """), {"state": "ABIERTO" if new == "PENDIENTE" else new, "id": order["id"]})
                                counts["estados_cambiados"] += 1
                                _write_change(conn,run_id,period,item,"CAMBIO_ESTADO",order["id"],before=old,after=new)
                        elif order["periodo"] < period:
                            # Los cierres de octubre son inmutables. El estado
                            # actualizado del backlog sí pertenece a noviembre.
                            if item["estado"] == "PENDIENTE" and not order["backlog_id"] and _status(order["estado"]) not in ("FINALIZADA","ANULADA"):
                                conn.execute(text("""
                                  INSERT INTO programacion.backlog_v2(
                                    orden_mantenimiento_id,semana_origen_inicio,semana_origen_fin,
                                    especialidad,motivo,movido_por,estado_seguimiento,
                                    primera_semana_origen_inicio,primera_semana_origen_fin)
                                  VALUES (:id,:from,:to,:spec,
                                    'ARRASTRE DESDE BASE DE DATOS GOOGLE SHEETS',
                                    'SINCRONIZACION_GOOGLE_SHEETS','PENDIENTE_DISPONIBLE',:from,:to)
                                  ON CONFLICT (orden_mantenimiento_id) DO NOTHING
                                """), {"id": order["id"], "from": prior_end, "to": prior_end, "spec": order["especialidad"]})
                                counts["backlog_conciliado"] += 1
                                _write_change(conn,run_id,period,item,"BACKLOG_AGREGADO",order["id"])
                            if item["estado"] == "FINALIZADA" and order["backlog_id"] and order["estado_seguimiento"] in ("PENDIENTE_DISPONIBLE","PENDIENTE_PROGRAMADA"):
                                conn.execute(text("""
                                  UPDATE programacion.backlog_v2
                                  SET estado_seguimiento='FINALIZADA',actualizado_en=now(),
                                      finalizado_en=coalesce(finalizado_en,now()),
                                      finalizado_por='GOOGLE_SHEETS_ESTADO_PROVISIONAL'
                                  WHERE id=:id AND estado_seguimiento IN ('PENDIENTE_DISPONIBLE','PENDIENTE_PROGRAMADA')
                                """), {"id": order["backlog_id"]})
                                counts["backlog_conciliado"] += 1
                                _write_change(conn,run_id,period,item,"BACKLOG_FINALIZADO_ORIGEN",order["id"])
                        elif order["has_closed"]:
                            if _status(order["estado"]) != item["estado"]:
                                counts["conflictos"] += 1
                                warnings.append(f"{ot}: cierre histórico protegido; estado de origen diferente")

                old_status = prior_snapshots.get(ot)
                if old_status != item["estado"]:
                    source_changes.append({
                        "run": run_id, "period": str(period), "ot": ot,
                        "order_id": order["id"] if order else None,
                        "action": "OBSERVACION_ORIGEN",
                        "before": old_status, "after": item["estado"],
                    })
                observations.append({
                    "period": str(period), "ot": ot, "spec": item["spec"],
                    "state": item["estado"], "plan": item["plan"],
                    "asset": item["asset"], "operation": item["operation"],
                    "row": item["row"], "run": run_id,
                })

            # Alta y actualización de fotografías en lotes: no realizar miles
            # de viajes SQL por cada consulta diaria de BASE DE DATOS.
            for offset in range(0, len(observations), 500):
                batch = observations[offset:offset + 500]
                conn.execute(text("""
                  INSERT INTO programacion.google_sheet_ot_estado_v2(
                    periodo,numero_ot,especialidad,estado,plan_trabajo,activo_codigo,
                    es_operacion,hoja_fila,observado_en,actualizado_en,ultima_sincronizacion_id)
                  SELECT CAST(s.period AS date),s.ot,s.spec,s.state,s.plan,s.asset,
                         s.operation,s.row,now(),now(),s.run
                  FROM jsonb_to_recordset(CAST(:payload AS jsonb))
                    AS s(period text,ot text,spec text,state text,plan text,asset text,
                         operation boolean,row integer,run bigint)
                  ON CONFLICT(periodo,numero_ot)
                  DO UPDATE SET estado=EXCLUDED.estado,especialidad=EXCLUDED.especialidad,
                    plan_trabajo=EXCLUDED.plan_trabajo,activo_codigo=EXCLUDED.activo_codigo,
                    es_operacion=EXCLUDED.es_operacion,hoja_fila=EXCLUDED.hoja_fila,
                    observado_en=CASE WHEN programacion.google_sheet_ot_estado_v2.estado IS DISTINCT FROM EXCLUDED.estado
                                      THEN now() ELSE programacion.google_sheet_ot_estado_v2.observado_en END,
                    actualizado_en=now(),ultima_sincronizacion_id=EXCLUDED.ultima_sincronizacion_id
                """), {"payload": json.dumps(batch)})
            for offset in range(0,len(source_changes),500):
                conn.execute(text("""
                  INSERT INTO programacion.google_sheet_sync_cambio_v2(
                    sincronizacion_id,periodo,numero_ot,orden_mantenimiento_id,
                    accion,estado_anterior,estado_nuevo)
                  SELECT s.run,CAST(s.period AS date),s.ot,s.order_id,
                         s.action,s.before,s.after
                  FROM jsonb_to_recordset(CAST(:payload AS jsonb))
                    AS s(run bigint,period text,ot text,order_id bigint,action text,
                         before text,after text)
                """), {"payload": json.dumps(source_changes[offset:offset+500])})

            # Actualizar el contador por plan sin borrar detalles históricos.
            for (plan, spec), quantity in group_ops.items():
                conn.execute(text("""
                  INSERT INTO programacion.operacion_exclusion_periodo_v2(
                    periodo,plan_clave_software,especialidad,cantidad,motivo,origen)
                  VALUES (:period,:plan,:spec,:quantity,'OPERACION','GOOGLE_SHEETS_BASE_SYNC')
                  ON CONFLICT(periodo,plan_clave_software,especialidad)
                  DO UPDATE SET cantidad=EXCLUDED.cantidad,actualizado_en=now()
                """), {"period": period, "plan": plan, "spec": spec, "quantity": quantity})
            weekly_count = _week_snapshots(conn,period,today,states,trigger)
            counts["seguimientos"] = weekly_count
            counts["conflictos"] += scan.get("duplicados_conflictivos",0)
            summary = {"fuente": "BASE DE DATOS", "periodo": str(period),
                       "filas_periodo": scan.get("filas_periodo",0),
                       "filas_repetidas": scan.get("filas_repetidas",0),
                       "ots_validas": len(states),
                       "nuevas": counts["nuevas"], "estados_cambiados": counts["estados_cambiados"],
                       "backlog_conciliado": counts["backlog_conciliado"],
                       "operaciones": counts["operaciones"],
                       "seguimientos_actualizados": counts["seguimientos"],
                       "conflictos": counts["conflictos"], "advertencias": warnings[:80],
                       "omitidas_por_datos": len(warnings)}
            conn.execute(text("""
              UPDATE programacion.google_sheet_sync_run_v2
              SET terminado_en=now(),filas_leidas=:read,ots_validas=:valid,
                ots_nuevas=:new,estados_cambiados=:changes,backlog_conciliado=:backlog,
                exclusiones_operacion=:ops,seguimientos_actualizados=:weekly,
                conflictos=:conflicts,resumen=CAST(:summary AS jsonb)
              WHERE id=:id
            """), {"id": run_id, "read": scan.get("filas_periodo",0), "valid": len(states),
                    "new": counts["nuevas"], "changes": counts["estados_cambiados"],
                    "backlog": counts["backlog_conciliado"], "ops": counts["operaciones"],
                    "weekly": weekly_count, "conflicts": counts["conflictos"],
                    "summary": json.dumps(summary,ensure_ascii=False)})
            return {"ok": True, "estado": "COMPLETADA", "sincronizacion_id": run_id, **summary}
    except SheetSyncError:
        raise
    except Exception as exc:
        # La transacción hace rollback completo; registrar solo error clasificado.
        with engine.begin() as conn:
            conn.execute(text("""
              INSERT INTO programacion.google_sheet_sync_run_v2(periodo,origen,estado,error_resumido)
              VALUES (:period,:origin,'ERROR',:detail)
            """), {"period": period, "origin": trigger, "detail": type(exc).__name__})
        raise SheetSyncError("No se completó la sincronización; no se aplicaron cambios parciales.") from exc


def sync_status(year: int, month: int) -> dict[str, Any]:
    period = date(year,month,1)
    with get_engine().connect() as conn:
        rows = [dict(row) for row in conn.execute(text("""
          SELECT id,estado,origen,iniciado_en,terminado_en,
                 filas_leidas,ots_validas,ots_nuevas,estados_cambiados,
                 backlog_conciliado,exclusiones_operacion,seguimientos_actualizados,
                 conflictos,resumen,error_resumido
          FROM programacion.google_sheet_sync_run_v2
          WHERE periodo=:period ORDER BY iniciado_en DESC,id DESC LIMIT 10
        """), {"period":period}).mappings()]
    return {
      "configurado": bool(os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON")),
      "origen": "BASE DE DATOS",
      "horario": "06:00 America/Bogota (11:00 UTC)",
      "periodo": str(period), "ultima": rows[0] if rows else None,
      "historial": rows,
    }
