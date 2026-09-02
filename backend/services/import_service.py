from __future__ import annotations

from collections import Counter
from sqlalchemy import text

from backend.database import get_engine
from backend.parsers.common import sha256_bytes
from backend.parsers.masters import (
    parse_master_assets, parse_master_plans, parse_master_classification,
    parse_master_personnel_turns,
)
from backend.parsers.operational import (
    parse_monthly_planning, parse_technician_roster, parse_order_states,
)

def _begin_import(conn, tipo, filename, content, **meta):
    return conn.execute(text("""INSERT INTO mantenimiento.importacion
      (tipo,nombre_archivo,sha256,estado,anio,mes,fecha_desde,fecha_hasta)
      VALUES(:tipo,:name,:sha,'PROCESANDO',:anio,:mes,:desde,:hasta) RETURNING id"""),
      {"tipo":tipo,"name":filename,"sha":sha256_bytes(content),"anio":meta.get("anio"),"mes":meta.get("mes"),"desde":meta.get("fecha_desde"),"hasta":meta.get("fecha_hasta")}).scalar_one()

def _finish(conn, iid, read, inserted, updated, rejected, warnings=None):
    state="COMPLETADA" if not rejected and not warnings else "CON_ADVERTENCIAS"
    msg=" | ".join((warnings or [])[:10]) or None
    conn.execute(text("""UPDATE mantenimiento.importacion SET estado=:e,filas_leidas=:r,filas_insertadas=:i,
      filas_actualizadas=:u,filas_rechazadas=:x,mensaje=:m WHERE id=:id"""),
      {"e":state,"r":read,"i":inserted,"u":updated,"x":rejected,"m":msg,"id":iid})
    return {"import_id":int(iid),"status":state,"rows_read":read,"inserted":inserted,"updated":updated,"rejected":rejected,"warnings":warnings or []}

def _error(conn,iid,row,entity,key,column,value,message,severity="ERROR"):
    conn.execute(text("""INSERT INTO mantenimiento.importacion_error
      (importacion_id,numero_fila,severidad,entidad,clave_externa,columna,valor_recibido,mensaje)
      VALUES(:i,:r,:s,:e,:k,:c,:v,:m)"""),
      {"i":iid,"r":row,"s":severity,"e":entity,"k":str(key or "")[:255],"c":column,"v":str(value or "")[:2000],"m":message})

def _spec_id(conn, code):
    return conn.execute(text("SELECT id FROM mantenimiento.especialidad WHERE codigo=:c"),{"c":code}).scalar_one_or_none()

def _plan_id(conn,spec,canonical):
    return conn.execute(text("""SELECT p.id FROM mantenimiento.plan_trabajo p
      JOIN mantenimiento.especialidad e ON e.id=p.especialidad_id
      WHERE e.codigo=:s AND p.nombre_canonico=:p"""),{"s":spec,"p":canonical}).scalar_one_or_none()

def import_master_assets(filename,content):
    parsed=parse_master_assets(content); ins=upd=rej=0
    with get_engine().begin() as conn:
        iid=_begin_import(conn,"MAESTRO_ACTIVOS",filename,content)
        parent_links=[]
        for r in parsed.rows:
            sid=_spec_id(conn,r["specialty"]) if r["specialty"] else None
            if r["specialty"] and not sid:
                _error(conn,iid,r["excel_row"],"activo",r["code"],"Especialidad",r["specialty"],"Especialidad no reconocida","ADVERTENCIA")
            exists=conn.execute(text("SELECT id FROM mantenimiento.activo WHERE codigo=:c"),{"c":r["code"]}).scalar_one_or_none()
            conn.execute(text("""INSERT INTO mantenimiento.activo
              (codigo,descripcion,criticidad,especialidad_id,estado_activo,area_nombre,linea_nombre,activo,actualizado_en)
              VALUES(:c,:d,:cr,:s,:st,:a,:l,TRUE,NOW())
              ON CONFLICT(codigo) DO UPDATE SET descripcion=EXCLUDED.descripcion,criticidad=EXCLUDED.criticidad,
              especialidad_id=COALESCE(EXCLUDED.especialidad_id,mantenimiento.activo.especialidad_id),
              estado_activo=EXCLUDED.estado_activo,area_nombre=EXCLUDED.area_nombre,linea_nombre=EXCLUDED.linea_nombre,
              actualizado_en=NOW()"""),
              {"c":r["code"],"d":r["description"],"cr":r["criticality"] or None,"s":sid,"st":r["state"] or None,"a":r["area"],"l":r["line"]})
            upd += 1 if exists else 0; ins += 0 if exists else 1
            if r["parent_code"]: parent_links.append((r["code"],r["parent_code"]))
        for child,parent in parent_links:
            conn.execute(text("""UPDATE mantenimiento.activo a SET activo_padre_id=p.id FROM mantenimiento.activo p
              WHERE a.codigo=:c AND p.codigo=:p"""),{"c":child,"p":parent})
        return _finish(conn,iid,len(parsed.rows),ins,upd,rej,parsed.warnings)

def import_master_plans(filename,content):
    parsed=parse_master_plans(content); ins=upd=rej=0
    with get_engine().begin() as conn:
        iid=_begin_import(conn,"MAESTRO_PLANES",filename,content)
        for r in parsed.rows:
            sid=_spec_id(conn,r["specialty"])
            if not sid:
                rej+=1; _error(conn,iid,r["excel_row"],"plan_trabajo",r["plan_raw"],"Especialidad",r["specialty"],"Especialidad no reconocida"); continue
            gid=conn.execute(text("""INSERT INTO mantenimiento.grupo_plan_trabajo(especialidad_id,nombre)
              VALUES(:s,:n) ON CONFLICT(especialidad_id,nombre) DO UPDATE SET activo=TRUE RETURNING id"""),{"s":sid,"n":r["group"]}).scalar_one()
            exists=_plan_id(conn,r["specialty"],r["plan_canonical"])
            pid=conn.execute(text("""INSERT INTO mantenimiento.plan_trabajo(especialidad_id,grupo_id,nombre,nombre_canonico,numero_personas)
              VALUES(:s,:g,:n,:c,:p) ON CONFLICT(especialidad_id,nombre_canonico) DO UPDATE SET
              grupo_id=EXCLUDED.grupo_id,nombre=EXCLUDED.nombre,
              numero_personas=COALESCE(EXCLUDED.numero_personas,mantenimiento.plan_trabajo.numero_personas),
              activo=TRUE RETURNING id"""),
              {"s":sid,"g":gid,"n":r["plan_raw"],"c":r["plan_canonical"],"p":r["persons"]}).scalar_one()
            upd += 1 if exists else 0; ins += 0 if exists else 1
        return _finish(conn,iid,len(parsed.rows),ins,upd,rej,parsed.warnings)

def import_master_classification(filename,content):
    parsed=parse_master_classification(content); ins=upd=rej=0
    with get_engine().begin() as conn:
        iid=_begin_import(conn,"MAESTRO_PLANES",filename,content)
        for r in parsed.rows:
            pid=_plan_id(conn,r["specialty"],r["plan_canonical"])
            if not pid:
                rej+=1; _error(conn,iid,r["excel_row"],"plan_trabajo",r["plan_raw"],"Plan de Trabajo",r["plan_raw"],"Plan no existe en maestro de planes"); continue
            exists=conn.execute(text("SELECT id FROM mantenimiento.plan_trabajo WHERE id=:p"),{"p":pid}).scalar_one_or_none()
            stopped=True if r["condition"]=="EQUIPO DETENIDO" else False if r["condition"]=="OPERANDO" else None
            conn.execute(text("""UPDATE mantenimiento.plan_trabajo
              SET numero_personas=COALESCE(:per,numero_personas),
                  equipo_detenido=COALESCE(:stopped,equipo_detenido),
                  actualizado_por='IMPORTACION_MAESTRO'
              WHERE id=:p"""),
              {"p":pid,"per":r["persons"],"stopped":stopped})
            upd += 1 if exists else 0
        return _finish(conn,iid,len(parsed.rows),ins,upd,rej,parsed.warnings)

def import_master_personnel_turns(filename,content):
    parsed=parse_master_personnel_turns(content); persons=parsed["personnel"]; turns=parsed["turns"]; ins=upd=rej=0
    with get_engine().begin() as conn:
        iid=_begin_import(conn,"MAESTRO_PERSONAL_TURNOS",filename,content)
        for r in persons.rows:
            sid=_spec_id(conn,r["specialty"])
            if not sid:
                rej+=1; _error(conn,iid,r["excel_row"],"tecnico",r["name"],"Especialidad",r["specialty"],"Especialidad no reconocida"); continue
            exists=conn.execute(text("SELECT id FROM mantenimiento.tecnico WHERE nombre_normalizado=:n"),{"n":r["normalized"]}).scalar_one_or_none()
            tid=conn.execute(text("""INSERT INTO mantenimiento.tecnico(nombre,nombre_normalizado,especialidad_id,activo)
              VALUES(:n,:nn,:s,TRUE) ON CONFLICT(nombre_normalizado) DO UPDATE SET nombre=EXCLUDED.nombre,
              especialidad_id=EXCLUDED.especialidad_id,activo=TRUE RETURNING id"""),{"n":r["name"],"nn":r["normalized"],"s":sid}).scalar_one()
            conn.execute(text("""INSERT INTO mantenimiento.tecnico_alias(tecnico_id,alias_normalizado) VALUES(:t,:a)
              ON CONFLICT(alias_normalizado) DO UPDATE SET tecnico_id=EXCLUDED.tecnico_id"""),{"t":tid,"a":r["normalized"]})
            upd += 1 if exists else 0; ins += 0 if exists else 1
        for r in turns.rows:
            exists=conn.execute(text("SELECT id FROM mantenimiento.turno WHERE codigo=:c"),{"c":r["code"]}).scalar_one_or_none()
            tid=conn.execute(text("""INSERT INTO mantenimiento.turno(codigo,codigo_estandar,horas_disponibles,es_ausencia,activo)
              VALUES(:c,:c,:h,:a,TRUE) ON CONFLICT(codigo) DO UPDATE SET horas_disponibles=EXCLUDED.horas_disponibles,
              es_ausencia=EXCLUDED.es_ausencia,activo=TRUE RETURNING id"""),
              {"c":r["code"],"h":r["hours"],"a":r["hours"]==0}).scalar_one()
            conn.execute(text("""INSERT INTO mantenimiento.turno_alias(alias_codigo,turno_id) VALUES(:a,:t)
              ON CONFLICT(alias_codigo) DO UPDATE SET turno_id=EXCLUDED.turno_id"""),{"a":r["raw_code"],"t":tid})
            upd += 1 if exists else 0; ins += 0 if exists else 1
        return _finish(conn,iid,len(persons.rows)+len(turns.rows),ins,upd,rej,persons.warnings+turns.warnings)

def import_monthly_planning(filename,content):
    parsed=parse_monthly_planning(content); dates=[r["planned_start"] for r in parsed.rows if r["planned_start"]]
    if not dates: raise ValueError("La planeación no contiene FechaPlaneadaInicio válida")
    counts=Counter((d.year,d.month) for d in dates); (year,month),_=counts.most_common(1)[0]
    ins=upd=rej=0
    with get_engine().begin() as conn:
        iid=_begin_import(conn,"PLANEACION_MENSUAL",filename,content,anio=year,mes=month)
        period=conn.execute(text("""INSERT INTO mantenimiento.periodo_mensual(anio,mes) VALUES(:y,:m)
          ON CONFLICT(anio,mes) DO UPDATE SET anio=EXCLUDED.anio RETURNING id"""),{"y":year,"m":month}).scalar_one()
        for r in parsed.rows:
            sid=_spec_id(conn,r["specialty"]); aid=conn.execute(text("SELECT id FROM mantenimiento.activo WHERE codigo=:c"),{"c":r["asset_code"]}).scalar_one_or_none()
            pid=_plan_id(conn,r["specialty"],r["plan_canonical"])
            missing=[]
            if not sid: missing.append("especialidad")
            if not aid: missing.append("activo")
            if not pid: missing.append("plan")
            if missing:
                rej+=1; _error(conn,iid,r["excel_row"],"pmp",r["asset_code"],None,None,"No se pudo relacionar: "+", ".join(missing)); continue
            exists=conn.execute(text("SELECT id FROM mantenimiento.pmp WHERE periodo_mensual_id=:pm AND source_key=:k"),{"pm":period,"k":r["source_key"]}).scalar_one_or_none()
            pmpid=conn.execute(text("""INSERT INTO mantenimiento.pmp(periodo_mensual_id,source_key,activo_id,plan_trabajo_id,especialidad_id,
              titulo,comentario,alerta,fecha_planeada_inicio,fecha_planeada_fin,fecha_fin_orden,orden_tipo,responsable,cronograma_planeacion,
              tiempo_planeado_min,importacion_id_ultima) VALUES(:pm,:k,:a,:p,:s,:t,:c,:al,:fi,:ff,:fo,:ot,:r,:cr,:min,:imp)
              ON CONFLICT(periodo_mensual_id,source_key) DO UPDATE SET activo_id=EXCLUDED.activo_id,plan_trabajo_id=EXCLUDED.plan_trabajo_id,
              especialidad_id=EXCLUDED.especialidad_id,titulo=EXCLUDED.titulo,comentario=EXCLUDED.comentario,alerta=EXCLUDED.alerta,
              fecha_planeada_inicio=EXCLUDED.fecha_planeada_inicio,fecha_planeada_fin=EXCLUDED.fecha_planeada_fin,fecha_fin_orden=EXCLUDED.fecha_fin_orden,
              orden_tipo=EXCLUDED.orden_tipo,responsable=EXCLUDED.responsable,cronograma_planeacion=EXCLUDED.cronograma_planeacion,
              tiempo_planeado_min=EXCLUDED.tiempo_planeado_min,importacion_id_ultima=EXCLUDED.importacion_id_ultima,actualizado_en=NOW() RETURNING id"""),
              {"pm":period,"k":r["source_key"],"a":aid,"p":pid,"s":sid,"t":r["title"],"c":r["comment"],"al":r["alert"],"fi":r["planned_start"],"ff":r["planned_end"],"fo":r["order_finished_at"],"ot":r["order_type"],"r":r["responsible"],"cr":r["planning_schedule"],"min":r["planned_minutes"],"imp":iid}).scalar_one()
            if r["order_number"]:
                conn.execute(text("""INSERT INTO mantenimiento.orden_mantenimiento(numero_orden,pmp_id,estado,fecha_finalizacion,importacion_id_ultima)
                  VALUES(:n,:p,:e,:f,:i) ON CONFLICT(numero_orden) DO UPDATE SET pmp_id=EXCLUDED.pmp_id,
                  estado=CASE WHEN mantenimiento.orden_mantenimiento.estado='FINALIZADA' THEN 'FINALIZADA' ELSE EXCLUDED.estado END,
                  fecha_finalizacion=COALESCE(EXCLUDED.fecha_finalizacion,mantenimiento.orden_mantenimiento.fecha_finalizacion),
                  importacion_id_ultima=EXCLUDED.importacion_id_ultima,actualizado_en=NOW()"""),
                  {"n":r["order_number"],"p":pmpid,"e":"FINALIZADA" if r["state"]=="FINALIZADA" else "PENDIENTE","f":r["order_finished_at"],"i":iid})
            upd += 1 if exists else 0; ins += 0 if exists else 1
        return _finish(conn,iid,len(parsed.rows),ins,upd,rej,parsed.warnings)

def import_technician_roster(filename,content,year=None,month=None):
    parsed=parse_technician_roster(content,year=year,month=month); ins=upd=rej=0
    with get_engine().begin() as conn:
        iid=_begin_import(conn,"PROGRAMACION_TECNICOS",filename,content,anio=parsed.metadata["year"],mes=parsed.metadata["month"])
        for r in parsed.rows:
            tech=conn.execute(text("""SELECT id FROM mantenimiento.tecnico WHERE nombre_normalizado=:n
              UNION SELECT tecnico_id FROM mantenimiento.tecnico_alias WHERE alias_normalizado=:n LIMIT 1"""),{"n":r["technician_normalized"]}).scalar_one_or_none()
            turn=conn.execute(text("""SELECT id FROM mantenimiento.turno WHERE codigo=:c
              UNION SELECT turno_id FROM mantenimiento.turno_alias WHERE alias_codigo=:c LIMIT 1"""),{"c":r["turn_code"]}).scalar_one_or_none()
            if not tech or not turn:
                rej+=1; _error(conn,iid,r["excel_row"],"programacion_tecnico",r["technician_name"],None,None,
                  ("Técnico no reconocido" if not tech else "Turno no reconocido")+f": {r['turn_raw']}"); continue
            exists=conn.execute(text("SELECT id FROM mantenimiento.programacion_tecnico WHERE tecnico_id=:t AND fecha=:f"),{"t":tech,"f":r["date"]}).scalar_one_or_none()
            conn.execute(text("""INSERT INTO mantenimiento.programacion_tecnico(tecnico_id,fecha,turno_id,importacion_id)
              VALUES(:t,:f,:tu,:i) ON CONFLICT(tecnico_id,fecha) DO UPDATE SET turno_id=EXCLUDED.turno_id,
              importacion_id=EXCLUDED.importacion_id,actualizado_en=NOW()"""),{"t":tech,"f":r["date"],"tu":turn,"i":iid})
            upd += 1 if exists else 0; ins += 0 if exists else 1
        return _finish(conn,iid,len(parsed.rows),ins,upd,rej,parsed.warnings)

def import_order_states(filename,content):
    parsed=parse_order_states(content); ins=upd=rej=0
    with get_engine().begin() as conn:
        iid=_begin_import(conn,"ESTADO_ORDENES",filename,content)
        for r in parsed.rows:
            oid=conn.execute(text("SELECT id FROM mantenimiento.orden_mantenimiento WHERE numero_orden=:n"),{"n":r["order_number"]}).scalar_one_or_none()
            if not oid:
                oid=conn.execute(text("""INSERT INTO mantenimiento.orden_mantenimiento(numero_orden,estado,fecha_finalizacion,importacion_id_ultima)
                  VALUES(:n,:e,:f,:i) RETURNING id"""),{"n":r["order_number"],"e":r["state"],"f":r["finished_at"],"i":iid}).scalar_one(); ins+=1
            else:
                conn.execute(text("""UPDATE mantenimiento.orden_mantenimiento SET estado=:e,fecha_finalizacion=COALESCE(:f,fecha_finalizacion),
                  importacion_id_ultima=:i,actualizado_en=NOW() WHERE id=:id"""),{"e":r["state"],"f":r["finished_at"],"i":iid,"id":oid}); upd+=1
            conn.execute(text("""INSERT INTO mantenimiento.orden_estado_historial(orden_id,estado,fecha_finalizacion,importacion_id)
              VALUES(:o,:e,:f,:i)"""),{"o":oid,"e":r["state"],"f":r["finished_at"],"i":iid})
        return _finish(conn,iid,len(parsed.rows),ins,upd,rej,parsed.warnings)
