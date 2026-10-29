from __future__ import annotations

from collections import defaultdict
from typing import Any
from sqlalchemy import text
from backend.database import get_engine
from backend.services.v2_week_tracking_service import V2WeeklyTrackingError, get_week_tracking as _get, record_week_tracking as _record

VALID = {"FINALIZADA", "PENDIENTE", "ANULADA"}

def _apply(data: dict[str, Any], overrides: dict[int, dict[str, Any]]) -> dict[str, Any]:
    rows = data.get("rows") or []
    for row in rows:
        automatic = "FINALIZADA" if row.get("finalizado") is True else "PENDIENTE" if row.get("finalizado") is False else None
        manual = (overrides.get(int(row["programacion_item_id"])) or {}).get("estado")
        effective = manual or automatic
        row["estado_automatico"] = automatic
        row["estado_manual"] = manual
        row["origen_estado"] = "MANUAL" if manual else ("AUTO_CALENDARIO" if automatic else "SIN_VALIDAR")
        row["discrepancia_manual_excel"] = bool(manual and automatic and manual != automatic)
        row["anulado"] = effective == "ANULADA"
        row["finalizado"] = True if effective == "FINALIZADA" else False if effective == "PENDIENTE" else None
        if manual:
            row.update({k: v for k, v in overrides[int(row["programacion_item_id"])].items() if k != "estado"})
    by_area: dict[str, dict[str, Any]] = defaultdict(lambda: {"programadas":0,"finalizadas":0,"pendientes":0,"anuladas":0,"hh_programadas":0.0,"hh_finalizadas":0.0,"hh_pendientes":0.0,"hh_anuladas":0.0})
    for row in rows:
        x=by_area[str(row.get("area_codigo") or "SIN ÁREA")]; hh=float(row.get("hh_programadas") or 0); x["programadas"]+=1; x["hh_programadas"]+=hh
        if row["finalizado"] is True: x["finalizadas"]+=1; x["hh_finalizadas"]+=hh
        elif row["finalizado"] is False: x["pendientes"]+=1; x["hh_pendientes"]+=hh
        elif row["anulado"]: x["anuladas"]+=1; x["hh_anuladas"]+=hh
    data["by_area"]=[{**v,"area_codigo":k,"avance_ot_pct":round(v["finalizadas"]*100/(v["programadas"]-v["anuladas"]),1) if v["programadas"]!=v["anuladas"] else 0,"avance_hh_pct":round(v["hh_finalizadas"]*100/(v["hh_programadas"]-v["hh_anuladas"]),1) if v["hh_programadas"]!=v["hh_anuladas"] else 0,"sin_coincidencia":v["programadas"]-v["finalizadas"]-v["pendientes"]-v["anuladas"]} for k,v in by_area.items()]
    finalized=sum(r["finalizado"] is True for r in rows); pending=sum(r["finalizado"] is False for r in rows); annulled=sum(bool(r["anulado"]) for r in rows); hh_finalized=sum(float(r.get("hh_programadas") or 0) for r in rows if r["finalizado"] is True); hh_annulled=sum(float(r.get("hh_programadas") or 0) for r in rows if r["anulado"]); hh_total=sum(float(r.get("hh_programadas") or 0) for r in rows)
    if data.get("latest"):
        data["latest"].update({"finalizados":finalized,"pendientes":pending,"anuladas":annulled,"sin_coincidencia":len(rows)-finalized-pending-annulled,"hh_finalizadas":round(hh_finalized,2),"hh_anuladas":round(hh_annulled,2),"avance_ot_pct":round(finalized*100/(len(rows)-annulled),1) if len(rows)!=annulled else 0,"avance_hh_pct":round(hh_finalized*100/(hh_total-hh_annulled),1) if hh_total!=hh_annulled else 0})
    return data

def get_week_tracking(programming_id:int) -> dict[str,Any]:
    data=_get(programming_id)
    with get_engine().connect() as conn:
        rows=[dict(r) for r in conn.execute(text("""SELECT sm.programacion_item_id,sm.estado,sm.comentario AS comentario_manual,sm.actualizado_por AS manual_actualizado_por,sm.actualizado_en AS manual_actualizado_en FROM programacion.seguimiento_estado_manual_v2 sm JOIN programacion.programacion_item_v2 pi ON pi.id=sm.programacion_item_id WHERE pi.programacion_id=:id"""),{"id":programming_id}).mappings()]
        audit=[dict(r) for r in conn.execute(text("""SELECT a.programacion_item_id,a.estado_anterior,a.estado_nuevo,a.comentario,a.actor,a.registrado_en FROM programacion.seguimiento_estado_manual_auditoria_v2 a JOIN programacion.programacion_item_v2 pi ON pi.id=a.programacion_item_id WHERE pi.programacion_id=:id ORDER BY a.registrado_en DESC,a.id DESC LIMIT 100"""),{"id":programming_id}).mappings()]
    data["manual_audit"]=audit
    return _apply(data,{int(r["programacion_item_id"]):r for r in rows})

def set_manual_status(programming_id:int,item_id:int,estado:str,comentario:str|None=None,recorded_by:str|None=None)->dict[str,Any]:
    estado=str(estado or "").upper().strip(); comentario=(comentario or "").strip() or None
    if estado not in VALID: raise V2WeeklyTrackingError("El estado manual solo puede ser FINALIZADA, PENDIENTE o ANULADA.")
    if estado=="ANULADA" and not comentario: raise V2WeeklyTrackingError("Para anular una OT debes indicar el motivo.")
    with get_engine().begin() as conn:
        item=conn.execute(text("""SELECT pi.id,p.estado FROM programacion.programacion_item_v2 pi JOIN programacion.programacion_semanal_v2 p ON p.id=pi.programacion_id WHERE pi.id=:item AND p.id=:programming FOR UPDATE"""),{"item":item_id,"programming":programming_id}).mappings().first()
        if not item: raise V2WeeklyTrackingError("La OT no pertenece a esta programación.")
        if item["estado"]=="CERRADA": raise V2WeeklyTrackingError("La semana ya está cerrada; el seguimiento es de solo lectura.")
        old=conn.execute(text("SELECT estado FROM programacion.seguimiento_estado_manual_v2 WHERE programacion_item_id=:item"),{"item":item_id}).scalar()
        conn.execute(text("""INSERT INTO programacion.seguimiento_estado_manual_v2(programacion_item_id,estado,comentario,actualizado_por) VALUES(:item,:estado,:comentario,:actor) ON CONFLICT(programacion_item_id) DO UPDATE SET estado=EXCLUDED.estado,comentario=EXCLUDED.comentario,actualizado_por=EXCLUDED.actualizado_por,actualizado_en=now()"""),{"item":item_id,"estado":estado,"comentario":comentario,"actor":recorded_by})
        conn.execute(text("INSERT INTO programacion.seguimiento_estado_manual_auditoria_v2(programacion_item_id,estado_anterior,estado_nuevo,comentario,actor) VALUES(:item,:old,:estado,:comentario,:actor)"),{"item":item_id,"old":old,"estado":estado,"comentario":comentario,"actor":recorded_by})
    return get_week_tracking(programming_id)

def record_week_tracking(**kwargs):
    _record(**kwargs)
    return get_week_tracking(kwargs["programming_id"])
