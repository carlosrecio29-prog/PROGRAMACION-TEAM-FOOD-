from __future__ import annotations
from datetime import date
from sqlalchemy import text
from backend.database import get_engine
from backend.services.query_service import get_capacity

class ProgrammingError(ValueError): pass

def _specialty_id(conn,code):
    v=conn.execute(text("SELECT id FROM mantenimiento.especialidad WHERE codigo=:c"),{"c":code.upper()}).scalar_one_or_none()
    if not v: raise ProgrammingError(f"Especialidad desconocida: {code}")
    return int(v)

def save_programming(*,date_from:date,date_to:date,specialty:str,pmp_ids:list[int],created_by=None,reason=None):
    if not pmp_ids: raise ProgrammingError("Debes seleccionar al menos un PMP")
    if date_to<date_from or (date_to-date_from).days>6: raise ProgrammingError("El rango semanal debe ser de 1 a 7 días")
    cap=get_capacity(date_from,date_to).get(specialty.upper(),{"available":0,"target":0,"standby":0})
    with get_engine().begin() as conn:
        sid=_specialty_id(conn,specialty)
        period=conn.execute(text("""INSERT INTO mantenimiento.periodo_semanal(fecha_desde,fecha_hasta) VALUES(:d,:h)
        ON CONFLICT(fecha_desde,fecha_hasta) DO UPDATE SET fecha_desde=EXCLUDED.fecha_desde RETURNING id"""),{"d":date_from,"h":date_to}).scalar_one()
        pid=conn.execute(text("""INSERT INTO mantenimiento.programacion_semanal(periodo_semanal_id,especialidad_id,estado,hh_disponibles,hh_objetivo,hh_standby,creado_por)
        VALUES(:p,:s,'GUARDADA',:a,:o,:st,:u) ON CONFLICT(periodo_semanal_id,especialidad_id) DO UPDATE SET estado='GUARDADA',
        hh_disponibles=EXCLUDED.hh_disponibles,hh_objetivo=EXCLUDED.hh_objetivo,hh_standby=EXCLUDED.hh_standby,guardado_en=NOW() RETURNING id"""),
        {"p":period,"s":sid,"a":cap["available"],"o":cap["target"],"st":cap["standby"],"u":created_by}).scalar_one()
        rows=conn.execute(text("""SELECT * FROM mantenimiento.vw_pmp_calculado WHERE pmp_id=ANY(:ids) AND especialidad=:s AND estado_orden<>'FINALIZADA'"""),{"ids":pmp_ids,"s":specialty.upper()}).mappings().all()
        if len(rows)!=len(set(pmp_ids)): raise ProgrammingError("Uno o más PMP no existen o ya están FINALIZADOS")
        incomplete=[r for r in rows if not r["datos_completos"]]
        if incomplete:
            faltantes=", ".join(sorted({x for r in incomplete for x in (r["datos_faltantes"] or [])}))
            raise ProgrammingError(f"Hay {len(incomplete)} PMP con datos incompletos ({faltantes}). Complétalos antes de programar.")
        total=sum(float(r["hh_pmp"]) for r in rows)
        if total>float(cap["target"] or 0)+.0001: raise ProgrammingError(f"La programación ({total:.1f} HH) supera la meta ({float(cap['target']):.1f} HH)")
        mx=conn.execute(text("SELECT COALESCE(MAX(numero_version),0) FROM mantenimiento.programacion_version WHERE programacion_semanal_id=:p"),{"p":pid}).scalar_one()
        ver=int(mx)+1
        conn.execute(text("UPDATE mantenimiento.programacion_version SET es_actual=FALSE WHERE programacion_semanal_id=:p AND es_actual=TRUE"),{"p":pid})
        vid=conn.execute(text("""INSERT INTO mantenimiento.programacion_version(programacion_semanal_id,numero_version,tipo,motivo,es_actual)
        VALUES(:p,:v,:t,:m,TRUE) RETURNING id"""),{"p":pid,"v":ver,"t":"INICIAL" if ver==1 else "REPROGRAMACION","m":reason}).scalar_one()
        for r in rows:
            backlog=conn.execute(text("SELECT 1 FROM mantenimiento.vw_backlog WHERE pmp_id=:p"),{"p":r["pmp_id"]}).scalar_one_or_none()
            conn.execute(text("""INSERT INTO mantenimiento.programacion_item(programacion_version_id,pmp_id,orden_id,origen,tiempo_planeado_min,personas_usar,hh_programadas,condicion_snapshot,criticidad_snapshot)
            VALUES(:v,:p,:o,:ori,:m,:per,:hh,:c,:cr)"""),{"v":vid,"p":r["pmp_id"],"o":r["orden_id"],"ori":"BACKLOG" if backlog else "MES","m":r["tiempo_planeado_min"],"per":r["personas_usar"],"hh":r["hh_pmp"],"c":r["condicion"],"cr":r["criticidad"]})
    return {"programming_id":int(pid),"version_id":int(vid),"version":ver,"hh_programmed":total,"hh_target":cap["target"]}

def programming_history(limit=50):
    with get_engine().connect() as conn:
        rows=conn.execute(text("""SELECT ps.id programming_id,pv.id version_id,pv.numero_version,pv.tipo,pv.es_actual,pv.creado_en,per.fecha_desde,per.fecha_hasta,e.codigo especialidad,
        ps.hh_disponibles,ps.hh_objetivo,ps.hh_standby,COALESCE(SUM(pi.hh_programadas),0)::float hh_programadas,COUNT(pi.id) items
        FROM mantenimiento.programacion_semanal ps JOIN mantenimiento.periodo_semanal per ON per.id=ps.periodo_semanal_id
        JOIN mantenimiento.especialidad e ON e.id=ps.especialidad_id JOIN mantenimiento.programacion_version pv ON pv.programacion_semanal_id=ps.id
        LEFT JOIN mantenimiento.programacion_item pi ON pi.programacion_version_id=pv.id GROUP BY ps.id,pv.id,per.id,e.id ORDER BY pv.creado_en DESC LIMIT :l"""),{"l":limit}).mappings().all()
    return [dict(r) for r in rows]

def programming_detail(version_id:int):
    with get_engine().connect() as conn:
        rows=conn.execute(text("""SELECT pi.id program_item_id,pi.pmp_id,om.numero_orden,a.codigo activo_codigo,a.descripcion activo_descripcion,a.area_nombre,a.linea_nombre,
        pt.nombre plan_trabajo,pi.criticidad_snapshot criticidad,pi.condicion_snapshot condicion,pi.personas_usar,pi.tiempo_planeado_min,pi.hh_programadas,pi.origen,
        COALESCE(om.estado,'PENDIENTE') estado FROM mantenimiento.programacion_item pi JOIN mantenimiento.pmp p ON p.id=pi.pmp_id
        JOIN mantenimiento.activo a ON a.id=p.activo_id JOIN mantenimiento.plan_trabajo pt ON pt.id=p.plan_trabajo_id
        LEFT JOIN mantenimiento.orden_mantenimiento om ON om.id=pi.orden_id WHERE pi.programacion_version_id=:v ORDER BY a.area_nombre,pt.nombre,a.codigo"""),{"v":version_id}).mappings().all()
    return [dict(r) for r in rows]

def close_programming(*,programming_id:int,version_id:int,reasons:dict,closed_by=None):
    with get_engine().begin() as conn:
        rows=conn.execute(text("""SELECT pi.id item_id,pi.hh_programadas,COALESCE(om.estado,'PENDIENTE') estado FROM mantenimiento.programacion_item pi
        LEFT JOIN mantenimiento.orden_mantenimiento om ON om.id=pi.orden_id WHERE pi.programacion_version_id=:v"""),{"v":version_id}).mappings().all()
        if not rows: raise ProgrammingError("La versión no tiene actividades")
        total=sum(float(r["hh_programadas"] or 0) for r in rows); final=sum(float(r["hh_programadas"] or 0) for r in rows if r["estado"]=="FINALIZADA"); pending=total-final; pct=final/total*100 if total else 0
        cid=conn.execute(text("""INSERT INTO mantenimiento.cierre_semanal(programacion_semanal_id,programacion_version_id,hh_programadas,hh_finalizadas,hh_pendientes,cumplimiento_pct,cerrado_por)
        VALUES(:p,:v,:t,:f,:pe,:pct,:u) ON CONFLICT(programacion_semanal_id,programacion_version_id) DO UPDATE SET hh_programadas=EXCLUDED.hh_programadas,
        hh_finalizadas=EXCLUDED.hh_finalizadas,hh_pendientes=EXCLUDED.hh_pendientes,cumplimiento_pct=EXCLUDED.cumplimiento_pct,cerrado_por=EXCLUDED.cerrado_por,cerrado_en=NOW() RETURNING id"""),
        {"p":programming_id,"v":version_id,"t":total,"f":final,"pe":pending,"pct":pct,"u":closed_by}).scalar_one()
        conn.execute(text("DELETE FROM mantenimiento.cierre_item WHERE cierre_semanal_id=:c"),{"c":cid})
        for r in rows:
            reason_id=None; detail=related=None
            if r["estado"]!="FINALIZADA":
                supplied=reasons.get(int(r["item_id"])) or {}; code=supplied.get("reason_code")
                if not code: raise ProgrammingError(f"Falta motivo para item {r['item_id']}")
                reason=conn.execute(text("SELECT id,requiere_detalle FROM mantenimiento.motivo_no_ejecucion WHERE codigo=:c AND activo=TRUE"),{"c":code}).mappings().one_or_none()
                if not reason: raise ProgrammingError(f"Motivo desconocido: {code}")
                detail=supplied.get("detail"); related=supplied.get("related_order")
                if reason["requiere_detalle"] and not detail: raise ProgrammingError(f"El motivo {code} requiere detalle")
                reason_id=reason["id"]
            conn.execute(text("""INSERT INTO mantenimiento.cierre_item(cierre_semanal_id,programacion_item_id,estado_ejecucion,motivo_no_ejecucion_id,detalle,orden_relacionada)
            VALUES(:c,:i,:s,:r,:d,:o)"""),{"c":cid,"i":r["item_id"],"s":r["estado"],"r":reason_id,"d":detail,"o":related})
        conn.execute(text("UPDATE mantenimiento.programacion_semanal SET estado='CERRADA',cerrado_en=NOW() WHERE id=:id"),{"id":programming_id})
    return {"closure_id":int(cid),"hh_programmed":total,"hh_finalized":final,"hh_pending":pending,"compliance_pct":pct}
