from __future__ import annotations

import io
import json
import os
from typing import Any
from urllib.parse import quote

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
from openpyxl import load_workbook
from sqlalchemy import text

from backend.database import get_engine
from backend.parsers.common import cell_by_header, header_mapping, normalize_text
from backend.parsers.team_food import normalize_state, scalar_text

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DEFAULT_TEAM_FOOD_SHEET_ID = "1pgUoKEX7FAVOwB4c9aUPdka_hsOr7ULZ1ntUqIOcNk0"


class GoogleSheetSyncError(RuntimeError):
    pass


def _config() -> dict[str, Any]:
    sheet_id = (os.getenv("TEAM_FOOD_SHEET_ID") or DEFAULT_TEAM_FOOD_SHEET_ID).strip()
    raw_credentials = (os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or "").strip()
    return {
        "sheet_id": sheet_id,
        "raw_credentials": raw_credentials,
        "configured": bool(sheet_id and raw_credentials),
    }


def google_sheet_status() -> dict[str, Any]:
    cfg = _config()
    return {
        "configured": cfg["configured"],
        "sheet_id": cfg["sheet_id"],
        "source": "Google Sheets · TEAM FOOD",
    }


def _credentials():
    cfg = _config()
    if not cfg["configured"]:
        return None

    try:
        info = json.loads(cfg["raw_credentials"])
    except json.JSONDecodeError as exc:
        raise GoogleSheetSyncError("GOOGLE_SERVICE_ACCOUNT_JSON no contiene un JSON válido") from exc

    if isinstance(info.get("private_key"), str):
        info["private_key"] = info["private_key"].replace("\\n", "\n")

    try:
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
    except Exception as exc:
        raise GoogleSheetSyncError("No se pudieron cargar las credenciales de Google") from exc


def _download_xlsx() -> bytes:
    cfg = _config()
    creds = _credentials()
    if creds is None:
        raise GoogleSheetSyncError("La conexión con Google Sheets todavía no está configurada")

    try:
        creds.refresh(GoogleAuthRequest())
    except Exception as exc:
        raise GoogleSheetSyncError("Google rechazó las credenciales configuradas") from exc

    url = (
        f"https://www.googleapis.com/drive/v3/files/{quote(cfg['sheet_id'], safe='')}/export"
        f"?mimeType={quote(XLSX_MIME, safe='')}"
    )
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=35,
        )
    except requests.RequestException as exc:
        raise GoogleSheetSyncError("No fue posible conectarse con Google Drive") from exc

    if response.status_code in {401, 403, 404}:
        email = ""
        try:
            email = json.loads(cfg["raw_credentials"]).get("client_email") or ""
        except Exception:
            pass
        hint = f" Comparte la hoja con {email} como lector." if email else ""
        raise GoogleSheetSyncError(
            f"Google no permitió leer la hoja TEAM FOOD (HTTP {response.status_code}).{hint}"
        )

    if not response.ok:
        raise GoogleSheetSyncError(
            f"No se pudo exportar TEAM FOOD desde Google Sheets (HTTP {response.status_code})"
        )

    if not response.content:
        raise GoogleSheetSyncError("Google devolvió la hoja TEAM FOOD vacía")

    return response.content


def _find_sheet(workbook, expected: str):
    key = normalize_text(expected)
    for ws in workbook.worksheets:
        if normalize_text(ws.title) == key:
            return ws
    return None


def _resolve_state(states: list[str]) -> tuple[str, bool]:
    clean = [normalize_state(value) for value in states if normalize_state(value)]
    clean = [value for value in clean if value != "ANULADA"]
    if not clean:
        return "NO ENCONTRADA", False

    unique = set(clean)
    if "PENDIENTE" in unique:
        return "PENDIENTE", len(unique) > 1
    if unique == {"FINALIZADA"}:
        return "FINALIZADA", False
    if len(unique) == 1:
        return clean[0], False
    return "REVISAR", True


def _read_live_states(content: bytes, order_numbers: set[str]) -> dict[str, dict[str, Any]]:
    if not order_numbers:
        return {}

    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = _find_sheet(workbook, "ORDENES MENSUALES")
    if ws is None:
        raise GoogleSheetSyncError("No se encontró la pestaña ORDENES MENSUALES en TEAM FOOD")

    mapping = header_mapping(ws, 1)
    raw: dict[str, list[str]] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        number = scalar_text(cell_by_header(row, mapping, "# DE ORDEN", "ORDEN"))
        if not number or number not in order_numbers:
            continue
        state = normalize_state(cell_by_header(row, mapping, "ESTADO"))
        if state:
            raw.setdefault(number, []).append(state)

    result: dict[str, dict[str, Any]] = {}
    for number, states in raw.items():
        state, conflict = _resolve_state(states)
        result[number] = {
            "state": state,
            "conflict": conflict,
            "sheet_rows": len(states),
        }
    return result


def sync_programming_statuses_from_google_sheet(*, version_id: int) -> dict[str, Any]:
    status = google_sheet_status()
    if not status["configured"]:
        return {
            **status,
            "synced": False,
            "matched": 0,
            "missing": 0,
            "conflicts": 0,
            "message": "Conexión de Google Sheets pendiente de configurar",
        }

    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT om.numero_orden
            FROM mantenimiento.programacion_item pi
            LEFT JOIN mantenimiento.orden_mantenimiento om ON om.id=pi.orden_id
            WHERE pi.programacion_version_id=:version_id
              AND om.numero_orden IS NOT NULL
              AND BTRIM(om.numero_orden)<>''
        """), {"version_id": version_id}).scalars().all()

    order_numbers = {str(value).strip() for value in rows if value}
    content = _download_xlsx()
    live = _read_live_states(content, order_numbers)

    update_rows = [
        {"number": number, "state": item["state"]}
        for number, item in live.items()
        if item["state"] in {"PENDIENTE", "FINALIZADA"}
    ]

    if update_rows:
        with get_engine().begin() as conn:
            conn.execute(text("""
                UPDATE mantenimiento.orden_mantenimiento
                SET estado=:state, actualizado_en=NOW()
                WHERE numero_orden=:number
            """), update_rows)

    missing = sorted(order_numbers - set(live))
    conflicts = sorted(number for number, item in live.items() if item["conflict"])

    return {
        **status,
        "synced": True,
        "matched": len(live),
        "missing": len(missing),
        "conflicts": len(conflicts),
        "missing_orders": missing[:25],
        "conflict_orders": conflicts[:25],
        "message": "Estados leídos directamente desde TEAM FOOD",
    }
