from __future__ import annotations

from datetime import date, datetime
import json
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text

from backend.database import get_engine
from backend.parsers.team_food import parse_team_food

VALID_CONDITIONS={"OPERANDO","EQUIPO DETENIDO","LINEA DETENIDA","AREA/PLANTA DETENIDA","SIN CLASIFICAR"}

def _chunks(rows:list[dict[str,Any]],size:int=500):
    for i in range(0,len(rows),size): yield rows[i:i+size]

def _execute_many(conn,sql:str,rows:list[dict[str,Any]],size:int=500):
    if not rows:return
    stmt=text(sql)
    for chunk in _chunks(rows,size):conn.execute(stmt,chunk)

def _begin_import(conn,filename:str,year:int,month:int,total:int):
    iid=conn.execute(text("""INSERT INTO mantenimiento.importacion(tipo,nombre_archivo,estado,anio,mes,filas_leidas)
      VALUES('MAESTRO_TEAM_FOOD',:f,'PROCESANDO',:y,:m,:n) RETURNING id"""),{"f":filename,"y":year,"m":month,"n":total}).scalar_one()
    sid=conn.execute(text("""INSERT INTO mantenimiento.sincronizacion_fuente_maestra(fuente,referencia,anio,mes,estado,filas_leidas)
      VALUES('TEAM_FOOD',:f,:y,:m,'PROCESANDO',:n) RETURNING id"""),{"f":filename,"y":year,"m":month,"n":total}).scalar_one()
    return int(iid),int(sid)

def _finish(conn,iid:int,sid:int,processed:int,rejected:int,warnings:list[str],summary:dict[str,Any]|None=None):
    state="COMPLETADA" if rejected==0 and not warnings else "CON_ADVERTENCIAS"
    msg=" | ".join(warnings[:12]) or None
    conn.execute(text("""UPDATE mantenimiento.importacion
      SET estado=:s,filas_insertadas=:p,filas_rechazadas=:r,mensaje=:m WHERE id=:i"""),
      {"s":state,"p":processed,"r":rejected,"m":msg,"i":iid})
    conn.execute(text("""UPDATE mantenimiento.sincronizacion_fuente_maestra
      SET estado=:s,filas_procesadas=:p,mensaje=:m,
      resumen_especialidad=CAST(:summary AS jsonb),finalizado_en=now() WHERE id=:i"""),
      {"s":state,"p":processed,"m":msg,"summary":json.dumps(summary or {}),"i":sid})
    return state

def import_team_food(filename:str,content:bytes,*,year:int|None=None,month:int|None=None)->dict[str,Any]:
    parsed=parse_team_food(content)
    orders=parsed["orders"].rows
    if not orders:raise ValueError("TEAM FOOD no contiene órdenes mensuales válidas")
    source_year=int(year or parsed["orders"].metadata.get("program_year") or datetime.now(ZoneInfo("America/Bogota")).year)
    available_months=sorted({int(r["month"]) for r in orders})
    target_month=int(month or max(available_months))
    if target_month not in available_months:
        raise ValueError(f"El mes {target_month} todavía no existe en ORDENES MENSUALES")

    warnings=[]
    for p in parsed.values():warnings.extend(p.warnings)
    total=sum(len(p.rows) for p in parsed.values())
    processed=rejected=0

    with get_engine().begin() as conn:
        iid,sync_id=_begin_import(conn,filename,source_year,target_month,total)
        spec_ids={r["codigo"]:int(r["id"]) for r in conn.execute(text("SELECT id,codigo FROM mantenimiento.especialidad")).mappings()}

        roster_code_by_name={}
        for r in parsed["roster"].rows:
            if r["external_code"]:
                roster_code_by_name.setdefault(r["technician_normalized"],r["external_code"])

        technician_rows=[]
        for r in parsed["technicians"].rows:
            sid=spec_ids.get(r["specialty"])
            if not sid:
                warnings.append(f"Especialidad no configurada para técnico {r['name']}: {r['specialty']}")
                continue
            technician_rows.append({
                "external":roster_code_by_name.get(r["name_normalized"]) or None,
                "name":r["name"],"normalized":r["name_normalized"],"sid":sid
            })
        if technician_rows:
            conn.execute(text("UPDATE mantenimiento.tecnico SET activo=false,codigo_externo=NULL"))
            _execute_many(conn,"""INSERT INTO mantenimiento.tecnico(codigo_externo,nombre,nombre_normalizado,especialidad_id,activo)
              VALUES(:external,:name,:normalized,:sid,true)
              ON CONFLICT(nombre_normalizado) DO UPDATE SET
              codigo_externo=COALESCE(excluded.codigo_externo,mantenimiento.tecnico.codigo_externo),
              nombre=excluded.nombre,especialidad_id=excluded.especialidad_id,activo=true""",technician_rows)
            processed+=len(technician_rows)


        asset_rows=[]
        for r in parsed["assets"].rows:
            if not r["code"]:continue
            asset_rows.append({"code":r["code"],"description":r["description"],"criticality":r["criticality"],
                "sid":spec_ids.get(r["specialty"]),"state":r["state"] or None,"area":r["area"],"line":r["line"]})
        _execute_many(conn,"""INSERT INTO mantenimiento.activo(codigo,descripcion,criticidad,especialidad_id,estado_activo,area_nombre,linea_nombre,activo,actualizado_en)
          VALUES(:code,:description,:criticality,:sid,:state,:area,:line,true,now())
          ON CONFLICT(codigo) DO UPDATE SET descripcion=excluded.descripcion,
          criticidad=COALESCE(excluded.criticidad,mantenimiento.activo.criticidad),
          especialidad_id=COALESCE(excluded.especialidad_id,mantenimiento.activo.especialidad_id),
          estado_activo=COALESCE(excluded.estado_activo,mantenimiento.activo.estado_activo),
          area_nombre=COALESCE(excluded.area_nombre,mantenimiento.activo.area_nombre),
          linea_nombre=COALESCE(excluded.linea_nombre,mantenimiento.activo.linea_nombre),actualizado_en=now()""",asset_rows)
        processed+=len(asset_rows)
        asset_map={r["codigo"]:dict(r) for r in conn.execute(text("SELECT id,codigo FROM mantenimiento.activo")).mappings()}

        groups={}
        for r in parsed["plans"].rows:
            sid=spec_ids.get(r["specialty"])
            if not sid:continue
            label=(f"{r['group_code']} - {r['group']}" if r["group_code"] else r["group"])[:255]
            groups[(sid,label)]={"sid":sid,"name":label}
        _execute_many(conn,"""INSERT INTO mantenimiento.grupo_plan_trabajo(especialidad_id,nombre,activo)
          VALUES(:sid,:name,true) ON CONFLICT(especialidad_id,nombre) DO UPDATE SET activo=true""",list(groups.values()))
        group_map={(r["especialidad_id"],r["nombre"]):int(r["id"]) for r in conn.execute(text("SELECT id,especialidad_id,nombre FROM mantenimiento.grupo_plan_trabajo")).mappings()}

        plan_rows=[]
        for r in parsed["plans"].rows:
            sid=spec_ids.get(r["specialty"])
            if not sid:rejected+=1;continue
            label=(f"{r['group_code']} - {r['group']}" if r["group_code"] else r["group"])[:255]
            plan_rows.append({"sid":sid,"gid":group_map.get((sid,label)),"name":r["plan_raw"],"canonical":r["plan_key"],
                "people":r["persons"],"execution":r["execution_minutes"],"stop":r["stop_minutes"]})
        _execute_many(conn,"""INSERT INTO mantenimiento.plan_trabajo(especialidad_id,grupo_id,nombre,nombre_canonico,personas_defecto,tiempo_ejecucion_min,tiempo_parada_min,fuente_maestra,activo)
          VALUES(:sid,:gid,:name,:canonical,:people,:execution,:stop,'TEAM_FOOD',true)
          ON CONFLICT(especialidad_id,nombre_canonico) DO UPDATE SET grupo_id=excluded.grupo_id,nombre=excluded.nombre,
          personas_defecto=COALESCE(excluded.personas_defecto,mantenimiento.plan_trabajo.personas_defecto),
          tiempo_ejecucion_min=COALESCE(excluded.tiempo_ejecucion_min,mantenimiento.plan_trabajo.tiempo_ejecucion_min),
          tiempo_parada_min=COALESCE(excluded.tiempo_parada_min,mantenimiento.plan_trabajo.tiempo_parada_min),
          fuente_maestra='TEAM_FOOD',activo=true""",plan_rows)
        processed+=len(plan_rows)

        plan_records=list(conn.execute(text("""SELECT p.id,p.nombre_canonico,p.tiempo_ejecucion_min,p.personas_defecto,e.codigo especialidad
          FROM mantenimiento.plan_trabajo p JOIN mantenimiento.especialidad e ON e.id=p.especialidad_id""")).mappings())
        plan_map={(r["especialidad"],r["nombre_canonico"]):dict(r) for r in plan_records}
        plan_by_key={}
        for r in plan_records:plan_by_key.setdefault(r["nombre_canonico"],dict(r))

        aliases=[{"pid":int(plan_map[(r["specialty"],r["plan_key"])]["id"]),"alias":r["plan_key"]}
          for r in parsed["plans"].rows if (r["specialty"],r["plan_key"]) in plan_map]
        _execute_many(conn,"""INSERT INTO mantenimiento.plan_trabajo_alias(plan_trabajo_id,alias_normalizado)
          VALUES(:pid,:alias) ON CONFLICT(alias_normalizado) DO UPDATE SET plan_trabajo_id=excluded.plan_trabajo_id""",aliases)

        classifications=[]
        for r in parsed["plans"].rows:
            rec=plan_map.get((r["specialty"],r["plan_key"]))
            if rec:classifications.append({"pid":int(rec["id"]),"condition":r["condition"],"people":r["persons"]})
        _execute_many(conn,"""INSERT INTO mantenimiento.clasificacion_plan(plan_trabajo_id,condicion,personas_usar,fuente,observacion)
          VALUES(:pid,'SIN CLASIFICAR',:people,'MAESTRO','Sincronizado desde TEAM FOOD')
          ON CONFLICT(plan_trabajo_id) DO UPDATE SET
          condicion=CASE
            WHEN mantenimiento.clasificacion_plan.fuente='USUARIO'
              THEN mantenimiento.clasificacion_plan.condicion
            ELSE 'SIN CLASIFICAR'
          END,
          personas_usar=CASE
            WHEN mantenimiento.clasificacion_plan.fuente='USUARIO'
                 AND mantenimiento.clasificacion_plan.personas_usar IS NOT NULL
              THEN mantenimiento.clasificacion_plan.personas_usar
            ELSE COALESCE(excluded.personas_usar,mantenimiento.clasificacion_plan.personas_usar)
          END,
          fuente=CASE
            WHEN mantenimiento.clasificacion_plan.fuente='USUARIO' THEN 'USUARIO'
            ELSE 'MAESTRO'
          END,
          actualizado_en=now()""",classifications)

        plan_source={r["plan_key"]:r for r in parsed["plans"].rows}
        activity_rows=[]
        for r in parsed["planning"].rows:
            if r["state"]!="HABILITADO":continue
            a=asset_map.get(r["asset_code"]);p=plan_by_key.get(r["plan_key"]);src=plan_source.get(r["plan_key"])
            if not a or not p:rejected+=1;continue
            activity_rows.append({"aid":int(a["id"]),"pid":int(p["id"]),"sid":spec_ids[p["especialidad"]],
                "time":src["execution_minutes"] if src else p["tiempo_ejecucion_min"],
                "people":src["persons"] if src else p["personas_defecto"],"iid":iid})
        _execute_many(conn,"""INSERT INTO mantenimiento.actividad_maestra(activo_id,plan_trabajo_id,especialidad_id,tiempo_estandar_min,personas_requeridas,fuente_datos,importacion_id_ultima,activo,actualizado_en)
          VALUES(:aid,:pid,:sid,:time,:people,'TEAM_FOOD',:iid,true,now())
          ON CONFLICT(activo_id,plan_trabajo_id,especialidad_id) DO UPDATE SET
          tiempo_estandar_min=COALESCE(excluded.tiempo_estandar_min,mantenimiento.actividad_maestra.tiempo_estandar_min),
          personas_requeridas=COALESCE(excluded.personas_requeridas,mantenimiento.actividad_maestra.personas_requeridas),
          fuente_datos='TEAM_FOOD',importacion_id_ultima=excluded.importacion_id_ultima,activo=true,actualizado_en=now()""",activity_rows)
        processed+=len(activity_rows)

        period_id=conn.execute(text("""INSERT INTO mantenimiento.periodo_mensual(anio,mes) VALUES(:y,:m)
          ON CONFLICT(anio,mes) DO UPDATE SET anio=excluded.anio RETURNING id"""),{"y":source_year,"m":target_month}).scalar_one()
        planning_lookup={}
        for r in parsed["planning"].rows:
            if r["state"]=="HABILITADO":planning_lookup[(r["asset_code"],r["description_key"])]=r
        selected=[r for r in orders if int(r["month"])==target_month and r["state"] in {"PENDIENTE","FINALIZADA"}]
        order_exceptions={}; pending_order_exceptions={}
        pmp_rows=[];order_context=[];asset_updates=[]
        for r in selected:
            link=planning_lookup.get((r["asset_code"],r["observation_key"]));asset=asset_map.get(r["asset_code"])
            if not link or not asset:
                rejected+=1
                order_exceptions[r["specialty"]]=order_exceptions.get(r["specialty"],0)+1
                if r["state"]=="PENDIENTE":
                    pending_order_exceptions[r["specialty"]]=pending_order_exceptions.get(r["specialty"],0)+1
                if len(warnings)<30:warnings.append(f"Fila {r['excel_row']}: no se relacionó activo/planeación")
                continue
            plan=plan_map.get((r["specialty"],link["plan_key"]))
            if not plan:
                rejected+=1
                order_exceptions[r["specialty"]]=order_exceptions.get(r["specialty"],0)+1
                if r["state"]=="PENDIENTE":
                    pending_order_exceptions[r["specialty"]]=pending_order_exceptions.get(r["specialty"],0)+1
                if len(warnings)<30:warnings.append(f"Fila {r['excel_row']}: plan no reconocido")
                continue
            minutes=r["minutes"] if r["minutes"] is not None else plan["tiempo_ejecucion_min"]
            pmp_rows.append({"period":period_id,"key":r["source_key"],"aid":int(asset["id"]),"pid":int(plan["id"]),
                "sid":spec_ids[r["specialty"]],"title":r["observation"],"date":r["programmed_at"],
                "minutes":float(minutes or 0),"iid":iid,"schedule":link["schedule_id"]})
            order_context.append((r,r["source_key"]))
            asset_updates.append({"code":r["asset_code"],"area":r["area"] or None,
                "crit":r["criticality"] if r["criticality"] in {"A","B","C"} else None})
        _execute_many(conn,"""UPDATE mantenimiento.activo SET area_nombre=COALESCE(:area,area_nombre),
          criticidad=COALESCE(:crit,criticidad),actualizado_en=now() WHERE codigo=:code""",asset_updates)
        _execute_many(conn,"""INSERT INTO mantenimiento.pmp(periodo_mensual_id,source_key,activo_id,plan_trabajo_id,especialidad_id,titulo,fecha_planeada_inicio,cronograma_planeacion,tiempo_planeado_min,importacion_id_ultima)
          VALUES(:period,:key,:aid,:pid,:sid,:title,:date,:schedule,:minutes,:iid)
          ON CONFLICT(periodo_mensual_id,source_key) DO UPDATE SET activo_id=excluded.activo_id,
          plan_trabajo_id=excluded.plan_trabajo_id,especialidad_id=excluded.especialidad_id,titulo=excluded.titulo,
          fecha_planeada_inicio=excluded.fecha_planeada_inicio,cronograma_planeacion=excluded.cronograma_planeacion,
          tiempo_planeado_min=excluded.tiempo_planeado_min,importacion_id_ultima=excluded.importacion_id_ultima,actualizado_en=now()""",pmp_rows)
        processed+=len(pmp_rows)
        pmp_map={r["source_key"]:int(r["id"]) for r in conn.execute(text("SELECT id,source_key FROM mantenimiento.pmp WHERE periodo_mensual_id=:p"),{"p":period_id}).mappings()}
        order_rows=[]
        for r,key in order_context:
            if r["order_number"] and key in pmp_map:
                order_rows.append({"number":r["order_number"],"pmp":pmp_map[key],"state":r["state"],"iid":iid})
        _execute_many(conn,"""INSERT INTO mantenimiento.orden_mantenimiento(numero_orden,pmp_id,estado,importacion_id_ultima,actualizado_en)
          VALUES(:number,:pmp,:state,:iid,now()) ON CONFLICT(numero_orden) DO UPDATE SET pmp_id=excluded.pmp_id,
          estado=excluded.estado,importacion_id_ultima=excluded.importacion_id_ultima,actualizado_en=now()""",order_rows)

        turn_rows=[{"code":"VA","hours":0.0,"absence":True},{"code":"IN","hours":0.0,"absence":True},{"code":"COMP","hours":0.0,"absence":True}]
        for r in parsed["turns"].rows:turn_rows.append({"code":r["code"],"hours":r["hours"],"absence":False})
        turn_rows=list({r["code"]:r for r in turn_rows}.values())
        _execute_many(conn,"""INSERT INTO mantenimiento.turno(codigo,codigo_estandar,horas_disponibles,es_ausencia,activo)
          VALUES(:code,:code,:hours,:absence,true) ON CONFLICT(codigo) DO UPDATE SET
          horas_disponibles=excluded.horas_disponibles,es_ausencia=excluded.es_ausencia,activo=true""",turn_rows)
        turn_map={r["codigo"]:int(r["id"]) for r in conn.execute(text("SELECT id,codigo FROM mantenimiento.turno")).mappings()}
        roster_year=int(year or parsed["roster"].metadata.get("year") or source_year)
        roster_month=int(month or parsed["roster"].metadata.get("month") or target_month)
        tech_rows=list(conn.execute(text("SELECT id,codigo_externo,nombre_normalizado FROM mantenimiento.tecnico WHERE activo=true")).mappings())
        tech_by_name={r["nombre_normalizado"]:dict(r) for r in tech_rows}
        tech_by_code={str(r["codigo_externo"]):dict(r) for r in tech_rows if r["codigo_externo"]}
        roster_rows=[]; missing_roster_techs=set(); missing_turn_codes=set()
        for r in parsed["roster"].rows:
            tech=tech_by_code.get(r["external_code"]) or tech_by_name.get(r["technician_normalized"])
            turn_id=turn_map.get(r["turn_code"])
            if not tech:
                missing_roster_techs.add(r["technician_name"])
                continue
            if not turn_id:
                missing_turn_codes.add(r["turn_code"])
                continue
            try:work_date=date(roster_year,roster_month,int(r["day"]))
            except ValueError:continue
            roster_rows.append({"tid":int(tech["id"]),"date":work_date,"turn":turn_id,"iid":iid})
        if missing_roster_techs:
            warnings.append("Sin especialidad maestra y excluidos de capacidad: "+", ".join(sorted(missing_roster_techs)))
        if missing_turn_codes:
            warnings.append("Turnos sin duración configurada y excluidos de capacidad: "+", ".join(sorted(missing_turn_codes)))
        _execute_many(conn,"""INSERT INTO mantenimiento.programacion_tecnico(tecnico_id,fecha,turno_id,importacion_id,actualizado_en)
          VALUES(:tid,:date,:turn,:iid,now()) ON CONFLICT(tecnico_id,fecha) DO UPDATE SET
          turno_id=excluded.turno_id,importacion_id=excluded.importacion_id,actualizado_en=now()""",roster_rows)
        processed+=len(roster_rows)

        source_summary=(parsed["orders"].metadata.get("monthly_summary") or {}).get(str(target_month),{})
        reconciliation={}
        for code in ("MEC","ELE","SER","MET"):
            base=dict(source_summary.get(code) or {
                "master_rows":0,"unique_ot":0,"pending_unique_ot":0,
                "finalized_unique_ot":0,"repeated_extra_rows":0
            })
            base["exceptions"]=int(order_exceptions.get(code,0))
            base["pending_exceptions"]=int(pending_order_exceptions.get(code,0))
            base["available_after_import"]=max(
                0,int(base.get("pending_unique_ot",0))-base["pending_exceptions"]
            )
            reconciliation[code]=base

        state=_finish(conn,iid,sync_id,processed,rejected,warnings,reconciliation)

    return {"status":state,"year":source_year,"month":target_month,"rows_read":total,
      "processed":processed,"rejected":rejected,"assets":len(asset_rows),"plans":len(plan_rows),
      "activities":len(activity_rows),"pmp":len(pmp_rows),"orders":len(order_rows),"technicians":len(technician_rows),"roster":len(roster_rows),
      "incomplete_people":sum(1 for r in parsed["plans"].rows if r["persons"] is None),
      "incomplete_condition":sum(1 for r in parsed["plans"].rows if r["condition"]=="SIN CLASIFICAR"),
      "warnings":warnings[:20]}

def learn_plan(*,plan_id:int,condition:str|None,people:float|None,updated_by:str|None=None)->dict[str,Any]:
    condition=(condition or "SIN CLASIFICAR").upper()
    if condition not in VALID_CONDITIONS:raise ValueError("Condición no válida")
    if people is not None and people<=0:raise ValueError("El número de personas debe ser mayor que cero")
    if condition=="SIN CLASIFICAR" and people is None:raise ValueError("Debes completar al menos un dato")
    with get_engine().begin() as conn:
        if not conn.execute(text("SELECT id FROM mantenimiento.plan_trabajo WHERE id=:p"),{"p":plan_id}).scalar_one_or_none():
            raise ValueError("Plan no encontrado")
        conn.execute(text("""INSERT INTO mantenimiento.clasificacion_plan(plan_trabajo_id,condicion,personas_usar,observacion,actualizado_por,fuente)
          VALUES(:p,:c,:n,'Aprendido durante la programación',:u,'USUARIO')
          ON CONFLICT(plan_trabajo_id) DO UPDATE SET
          condicion=CASE WHEN :c='SIN CLASIFICAR' THEN mantenimiento.clasificacion_plan.condicion ELSE :c END,
          personas_usar=COALESCE(:n,mantenimiento.clasificacion_plan.personas_usar),
          observacion='Aprendido durante la programación',actualizado_por=:u,fuente='USUARIO',actualizado_en=now()"""),
          {"p":plan_id,"c":condition,"n":people,"u":updated_by})
        if people is not None and updated_by!="PRUEBA_WEB":
            conn.execute(text("UPDATE mantenimiento.plan_trabajo SET personas_defecto=:n,actualizado_por=:u WHERE id=:p"),
              {"n":people,"u":updated_by,"p":plan_id})
        row=conn.execute(text("""SELECT p.id plan_id,p.nombre,cp.condicion,
          COALESCE(cp.personas_usar,p.personas_defecto) personas
          FROM mantenimiento.plan_trabajo p
          LEFT JOIN mantenimiento.clasificacion_plan cp ON cp.plan_trabajo_id=p.id WHERE p.id=:p"""),
          {"p":plan_id}).mappings().one()
    return dict(row)
