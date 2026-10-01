from __future__ import annotations

from datetime import date
from html import escape
from io import BytesIO
from typing import Any

from sqlalchemy import text

from backend.database import get_engine

VALID_SPECIALTIES={"MEC","ELE","MET","SER"}


class V2ProgrammingError(ValueError):
    pass


def capacity_split(available: float) -> dict[str, float]:
    available = round(float(available or 0), 2)
    effective = round(available * 0.80, 2)
    preventive = round(effective * 0.80, 2)
    corrective = round(effective * 0.20, 2)
    initial_margin = round(available - effective, 2)
    return {
        "available": available,
        "effective": effective,
        "preventive": preventive,
        "corrective": corrective,
        "initial_margin": initial_margin,
    }


def _validate_week(date_from:date,date_to:date,specialty:str)->str:
    specialty=specialty.upper()
    if specialty not in VALID_SPECIALTIES:
        raise V2ProgrammingError("Especialidad inválida")
    if date_to<date_from:
        raise V2ProgrammingError("La fecha final no puede ser anterior a la inicial")
    if (date_to-date_from).days>6:
        raise V2ProgrammingError("La programación debe abarcar máximo 7 días")
    return specialty


def _capacity(conn,date_from:date,date_to:date,specialty:str)->dict[str,Any]:
    row=conn.execute(text("""
        SELECT
          count(DISTINCT t.id)::int AS tecnicos_asignados,
          count(DISTINCT t.id) FILTER (WHERE pt.horas_disponibles > 0)::int AS tecnicos_disponibles,
          round(COALESCE(sum(pt.horas_disponibles),0),2) AS hh_disponibles
        FROM programacion.programacion_tecnico pt
        JOIN programacion.tecnico t ON t.id=pt.tecnico_id
        WHERE pt.fecha BETWEEN :date_from AND :date_to
          AND t.especialidad_efectiva=:specialty
    """),{"date_from":date_from,"date_to":date_to,"specialty":specialty}).mappings().one()
    split=capacity_split(float(row["hh_disponibles"] or 0))
    available=split["available"]
    effective=split["effective"]
    target=split["preventive"]
    reserve=split["corrective"]
    initial_margin=split["initial_margin"]
    technicians_available=int(row["tecnicos_disponibles"] or 0)
    technicians_assigned=int(row["tecnicos_asignados"] or 0)
    return {
        "technicians":technicians_available,
        "technicians_available":technicians_available,
        "technicians_assigned":technicians_assigned,
        "available":round(available,2),
        "effective":effective,
        "target":target,
        "reserve":reserve,
        "preventive":target,
        "corrective":reserve,
        "initial_margin":initial_margin,
    }


def _monthly_demand(conn, month_date: date, specialty: str, exclude_programming_id: int | None = None) -> dict[str, Any]:
    period = month_date.replace(day=1)
    row = conn.execute(text("""
        WITH candidate AS (
          SELECT
            o.id AS orden_mantenimiento_id,
            CASE
              WHEN p.numero_personas_efectivo IS NOT NULL
               AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
              THEN round(
                COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0
                * p.numero_personas_efectivo,
                2
              )
              ELSE NULL
            END AS hh,
            upper(COALESCE(o.estado,'')) LIKE 'FINALIZ%' AS finalizada_software
          FROM programacion.orden_mantenimiento o
          JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
          WHERE o.especialidad=:specialty
            AND o.periodo=:period
            AND NOT COALESCE(p.es_operacion,false)
        ),
        coverage AS (
          SELECT
            c.*,
            CASE
              WHEN c.finalizada_software THEN true
              WHEN EXISTS (
                SELECT 1
                FROM programacion.programacion_item_v2 pi
                JOIN programacion.programacion_semanal_v2 ps ON ps.id=pi.programacion_id
                WHERE pi.orden_mantenimiento_id=c.orden_mantenimiento_id
                  AND (
                    CAST(:exclude_programming_id AS bigint) IS NULL
                    OR pi.programacion_id<>CAST(:exclude_programming_id AS bigint)
                  )
                  AND (
                    ps.estado<>'CERRADA'
                    OR COALESCE(pi.finalizado,false)=true
                  )
              ) THEN true
              ELSE false
            END AS cubierta
          FROM candidate c
        )
        SELECT
          count(*)::int AS pmp_count,
          count(*) FILTER (WHERE hh IS NULL)::int AS missing_hh_count,
          round(COALESCE(sum(hh),0),2) AS pmp_hh,
          count(*) FILTER (WHERE cubierta)::int AS covered_count_base,
          round(COALESCE(sum(hh) FILTER (WHERE cubierta),0),2) AS covered_hh_base
        FROM coverage
    """), {
        "period": period,
        "specialty": specialty,
        "exclude_programming_id": exclude_programming_id,
    }).mappings().one()

    total_count = int(row["pmp_count"] or 0)
    total_hh = round(float(row["pmp_hh"] or 0), 2)
    covered_count = int(row["covered_count_base"] or 0)
    covered_hh = round(float(row["covered_hh_base"] or 0), 2)
    return {
        "period": period.isoformat(),
        "pmp_count": total_count,
        "pmp_hh": total_hh,
        "missing_hh_count": int(row["missing_hh_count"] or 0),
        "covered_count_base": min(total_count, covered_count),
        "covered_hh_base": min(total_hh, covered_hh),
        "pending_count_base": max(0, total_count-covered_count),
        "pending_hh_base": round(max(0.0, total_hh-covered_hh), 2),
    }


def refresh_open_program_capacities(conn)->int:
    rows=conn.execute(text("""
        SELECT id,semana_inicio,semana_fin,especialidad
        FROM programacion.programacion_semanal_v2
        WHERE estado<>'CERRADA'
    """)).mappings().all()
    updated=0
    for row in rows:
        capacity=_capacity(
            conn,
            row["semana_inicio"],
            row["semana_fin"],
            row["especialidad"],
        )
        conn.execute(text("""
            UPDATE programacion.programacion_semanal_v2
            SET hh_disponibles=:available,
                hh_objetivo=:target,
                hh_reserva=:reserve,
                actualizado_en=now()
            WHERE id=:id
        """),{
            "available":capacity["available"],
            "target":capacity["target"],
            "reserve":capacity["reserve"],
            "id":row["id"],
        })
        updated+=1
    return updated


def get_week_programming(*,date_from:date,date_to:date,specialty:str)->dict[str,Any]:
    specialty=_validate_week(date_from,date_to,specialty)
    with get_engine().connect() as conn:
        capacity=_capacity(conn,date_from,date_to,specialty)
        programming=conn.execute(text("""
            SELECT id,estado,hh_disponibles,hh_objetivo,hh_reserva,creado_en,actualizado_en,emitido_en
            FROM programacion.programacion_semanal_v2
            WHERE semana_inicio=:date_from
              AND semana_fin=:date_to
              AND especialidad=:specialty
        """),{"date_from":date_from,"date_to":date_to,"specialty":specialty}).mappings().first()
        programming_id=int(programming["id"]) if programming else None

        rows=[dict(r) for r in conn.execute(text("""
            WITH candidate AS (
              SELECT DISTINCT ON (o.id)
                o.id AS orden_mantenimiento_id,
                o.numero_ot,
                o.titulo,
                o.estado,
                o.especialidad,
                o.periodo,
                a.codigo AS activo_codigo,
                a.descripcion AS activo_descripcion,
                a.area_codigo,
                root.descripcion AS area_nombre,
                p.id AS plan_trabajo_id,
                p.plan_trabajo,
                p.descripcion_grupo,
                p.numero_personas_efectivo,
                p.tiempo_parada_efectivo_min,
                p.requiere_parada,
                COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) AS tiempo_min,
                round(COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0*p.numero_personas_efectivo,2) AS hh,
                b.id AS backlog_id,
                b.semana_origen_inicio,
                b.semana_origen_fin,
                b.movido_en
              FROM programacion.orden_mantenimiento o
              JOIN programacion.activo a ON a.id=o.activo_id
              LEFT JOIN programacion.activo root ON root.codigo='BA-'||a.area_codigo
              JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              LEFT JOIN programacion.backlog_v2 b
                ON b.orden_mantenimiento_id=o.id
               AND b.especialidad=:specialty
              LEFT JOIN programacion.programacion_item_v2 ci
                ON ci.orden_mantenimiento_id=o.id
               AND ci.programacion_id=CAST(:programming_id AS bigint)
              WHERE o.especialidad=:specialty
                AND (
                  o.periodo=date_trunc('month',CAST(:date_from AS date))::date
                  OR b.id IS NOT NULL
                  OR ci.id IS NOT NULL
                )
                AND upper(COALESCE(o.estado,''))<>'FINALIZADO'
                AND p.numero_personas_efectivo IS NOT NULL
                AND p.tiempo_parada_efectivo_min IS NOT NULL
                AND p.requiere_parada IS NOT NULL
                AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
              ORDER BY o.id,b.movido_en DESC NULLS LAST
            )
            SELECT
              c.*,
              CASE WHEN current_item.id IS NOT NULL THEN true ELSE false END AS seleccionado,
              CASE WHEN c.backlog_id IS NOT NULL AND current_item.id IS NULL THEN true ELSE false END AS es_backlog
            FROM candidate c
            LEFT JOIN programacion.programacion_item_v2 current_item
              ON current_item.orden_mantenimiento_id=c.orden_mantenimiento_id
             AND current_item.programacion_id=CAST(:programming_id AS bigint)
            WHERE NOT EXISTS (
              SELECT 1
              FROM programacion.programacion_item_v2 other_item
              JOIN programacion.programacion_semanal_v2 other_program ON other_program.id=other_item.programacion_id
              WHERE other_item.orden_mantenimiento_id=c.orden_mantenimiento_id
                AND (CAST(:programming_id AS bigint) IS NULL OR other_program.id<>CAST(:programming_id AS bigint))
            )
            ORDER BY c.area_codigo,c.numero_ot NULLS LAST,c.activo_codigo,c.plan_trabajo
        """),{"date_from":date_from,"specialty":specialty,"programming_id":programming_id}).mappings()]

        selected_hh=round(sum(float(r["hh"] or 0) for r in rows if r["seleccionado"]),2)

    backlog=[r for r in rows if r["es_backlog"]]
    regular=[r for r in rows if not r["es_backlog"]]
    operating=[r for r in regular if r["requiere_parada"] is False]
    stopped=[r for r in regular if r["requiere_parada"] is True]
    return {
        "date_from":str(date_from),
        "date_to":str(date_to),
        "specialty":specialty,
        "capacity":capacity,
        "programming":dict(programming) if programming else None,
        "selected_hh":selected_hh,
        "selected_ids":[int(r["orden_mantenimiento_id"]) for r in rows if r["seleccionado"]],
        "operating":operating,
        "stopped":stopped,
        "backlog":backlog,
        "backlog_count":len(backlog),
    }


def save_week_programming(*,date_from:date,date_to:date,specialty:str,order_ids:list[int],created_by:str|None=None)->dict[str,Any]:
    specialty=_validate_week(date_from,date_to,specialty)
    unique_ids=list(dict.fromkeys(int(x) for x in order_ids))
    if not unique_ids:
        raise V2ProgrammingError("Debes seleccionar al menos una orden/actividad")

    with get_engine().begin() as conn:
        capacity=_capacity(conn,date_from,date_to,specialty)
        if capacity["target"]<=0:
            raise V2ProgrammingError("Esta especialidad no tiene H-H disponibles para la semana seleccionada")

        current_id=conn.execute(text("""
            SELECT id FROM programacion.programacion_semanal_v2
            WHERE semana_inicio=:date_from AND semana_fin=:date_to AND especialidad=:specialty
        """),{"date_from":date_from,"date_to":date_to,"specialty":specialty}).scalar_one_or_none()

        previous_ids=[]
        if current_id:
            previous_ids=[int(x) for x in conn.execute(text("""
                SELECT orden_mantenimiento_id
                FROM programacion.programacion_item_v2
                WHERE programacion_id=:id
            """),{"id":current_id}).scalars().all()]

        rows=[dict(r) for r in conn.execute(text("""
            SELECT o.id AS orden_mantenimiento_id,o.numero_ot,p.requiere_parada,
              round(COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0*p.numero_personas_efectivo,2) AS hh
            FROM programacion.orden_mantenimiento o
            JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.id=ANY(CAST(:ids AS bigint[]))
              AND o.especialidad=:specialty
              AND upper(COALESCE(o.estado,''))<>'FINALIZADO'
              AND p.numero_personas_efectivo IS NOT NULL
              AND p.tiempo_parada_efectivo_min IS NOT NULL
              AND p.requiere_parada IS NOT NULL
              AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
        """),{"ids":unique_ids,"specialty":specialty}).mappings()]
        if len(rows)!=len(unique_ids):
            raise V2ProgrammingError("Una o más órdenes ya no están disponibles o tienen datos incompletos")

        conflicts=conn.execute(text("""
            SELECT o.numero_ot,ps.semana_inicio,ps.semana_fin,ps.especialidad
            FROM programacion.programacion_item_v2 pi
            JOIN programacion.programacion_semanal_v2 ps ON ps.id=pi.programacion_id
            JOIN programacion.orden_mantenimiento o ON o.id=pi.orden_mantenimiento_id
            WHERE pi.orden_mantenimiento_id=ANY(CAST(:ids AS bigint[]))
              AND (CAST(:current_id AS bigint) IS NULL OR ps.id<>CAST(:current_id AS bigint))
            LIMIT 10
        """),{"ids":unique_ids,"current_id":current_id}).mappings().all()
        if conflicts:
            first=conflicts[0]
            raise V2ProgrammingError(f"La OT {first['numero_ot'] or 'SIN ASIGNAR'} ya está programada del {first['semana_inicio']} al {first['semana_fin']}")

        total=round(sum(float(r["hh"] or 0) for r in rows),2)
        if total>capacity["target"]+.001:
            raise V2ProgrammingError(f"La selección suma {total:.1f} H-H y supera la meta preventiva ({capacity['target']:.1f} H-H), equivalente al 80% de las H-H efectivas")

        programming_id=conn.execute(text("""
            INSERT INTO programacion.programacion_semanal_v2(
              semana_inicio,semana_fin,especialidad,hh_disponibles,hh_objetivo,hh_reserva,estado,creado_por,actualizado_en
            ) VALUES(:date_from,:date_to,:specialty,:available,:target,:reserve,'GUARDADA',:created_by,now())
            ON CONFLICT(semana_inicio,semana_fin,especialidad)
            DO UPDATE SET hh_disponibles=EXCLUDED.hh_disponibles,hh_objetivo=EXCLUDED.hh_objetivo,
              hh_reserva=EXCLUDED.hh_reserva,estado='GUARDADA',
              creado_por=COALESCE(EXCLUDED.creado_por,programacion.programacion_semanal_v2.creado_por),actualizado_en=now()
            RETURNING id
        """),{"date_from":date_from,"date_to":date_to,"specialty":specialty,
              "available":capacity["available"],"target":capacity["target"],"reserve":capacity["reserve"],"created_by":created_by}).scalar_one()

        removed_ids=sorted(set(previous_ids)-set(unique_ids))
        if removed_ids:
            conn.execute(text("""
                INSERT INTO programacion.backlog_v2(
                  orden_mantenimiento_id,programacion_origen_id,semana_origen_inicio,semana_origen_fin,
                  especialidad,motivo,movido_por,movido_en,actualizado_en
                )
                SELECT x,:programming_id,:date_from,:date_to,:specialty,
                       'RETIRADA DE PROGRAMACIÓN SEMANAL',:created_by,now(),now()
                FROM unnest(CAST(:removed_ids AS bigint[])) AS x
                ON CONFLICT(orden_mantenimiento_id)
                DO UPDATE SET programacion_origen_id=EXCLUDED.programacion_origen_id,
                  semana_origen_inicio=EXCLUDED.semana_origen_inicio,semana_origen_fin=EXCLUDED.semana_origen_fin,
                  especialidad=EXCLUDED.especialidad,motivo=EXCLUDED.motivo,movido_por=EXCLUDED.movido_por,
                  movido_en=now(),actualizado_en=now()
            """),{"programming_id":programming_id,"date_from":date_from,"date_to":date_to,
                  "specialty":specialty,"created_by":created_by,"removed_ids":removed_ids})

        conn.execute(text("DELETE FROM programacion.backlog_v2 WHERE orden_mantenimiento_id=ANY(CAST(:ids AS bigint[]))"),{"ids":unique_ids})
        conn.execute(text("DELETE FROM programacion.programacion_item_v2 WHERE programacion_id=:programming_id"),{"programming_id":programming_id})
        for row in rows:
            conn.execute(text("""
                INSERT INTO programacion.programacion_item_v2(programacion_id,orden_mantenimiento_id,hh_programadas,requiere_parada)
                VALUES(:programming_id,:order_id,:hh,:requires_stop)
            """),{"programming_id":programming_id,"order_id":row["orden_mantenimiento_id"],"hh":row["hh"],"requires_stop":row["requiere_parada"]})

    return {
        "ok":True,"programming_id":int(programming_id),"hh_available":capacity["available"],
        "hh_target":capacity["target"],"hh_reserve":capacity["reserve"],"hh_programmed":total,
        "progress_pct":round(total/capacity["target"]*100,1) if capacity["target"] else 0,
        "items":len(rows),"moved_to_backlog":len(removed_ids),
    }


def _report_data(programming_id:int)->tuple[dict[str,Any],list[dict[str,Any]]]:
    with get_engine().connect() as conn:
        header=conn.execute(text("""
            SELECT ps.id,ps.semana_inicio,ps.semana_fin,ps.especialidad,ps.hh_disponibles,ps.hh_objetivo,ps.hh_reserva,
              ps.estado,ps.creado_por,ps.creado_en,ps.actualizado_en,
              round(COALESCE(sum(pi.hh_programadas),0),2) AS hh_programadas,count(pi.id)::int AS items
            FROM programacion.programacion_semanal_v2 ps
            LEFT JOIN programacion.programacion_item_v2 pi ON pi.programacion_id=ps.id
            WHERE ps.id=:id GROUP BY ps.id
        """),{"id":programming_id}).mappings().first()
        if not header: raise V2ProgrammingError("Programación no encontrada")
        rows=[dict(r) for r in conn.execute(text("""
            SELECT o.id AS orden_mantenimiento_id,o.periodo,o.numero_ot,a.area_codigo,COALESCE(root.descripcion,a.area_codigo) AS area_nombre,
              a.codigo AS activo_codigo,a.descripcion AS activo_descripcion,p.descripcion_grupo,p.plan_trabajo,
              p.numero_personas_efectivo AS personas,COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) AS tiempo_min,
              pi.hh_programadas,pi.requiere_parada,pi.origen,a.criticidad,
              CASE WHEN pi.requiere_parada THEN 'EQUIPO DETENIDO' ELSE 'EQUIPO FUNCIONANDO' END AS condicion
            FROM programacion.programacion_item_v2 pi
            JOIN programacion.orden_mantenimiento o ON o.id=pi.orden_mantenimiento_id
            JOIN programacion.activo a ON a.id=o.activo_id
            LEFT JOIN programacion.activo root ON root.codigo='BA-'||a.area_codigo
            JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE pi.programacion_id=:id
            ORDER BY pi.requiere_parada,a.area_codigo,o.numero_ot NULLS LAST,a.codigo
        """),{"id":programming_id}).mappings()]
        monthly=_monthly_demand(
            conn,
            header["semana_inicio"],
            header["especialidad"],
            programming_id,
        )
        month_period=header["semana_inicio"].replace(day=1)
        selected_month_rows=[
            row for row in rows
            if row.get("periodo")==month_period
        ]
        selected_month_ids={
            int(row["orden_mantenimiento_id"])
            for row in selected_month_rows
            if row.get("orden_mantenimiento_id") is not None
        }
        selected_month_hh=round(sum(float(row.get("hh_programadas") or 0) for row in selected_month_rows),2)
        monthly["covered_count"]=min(
            monthly["pmp_count"],
            monthly["covered_count_base"]+len(selected_month_ids),
        )
        monthly["covered_hh"]=round(min(
            monthly["pmp_hh"],
            monthly["covered_hh_base"]+selected_month_hh,
        ),2)
        monthly["pending_count"]=max(0,monthly["pmp_count"]-monthly["covered_count"])
        monthly["pending_hh"]=round(max(0.0,monthly["pmp_hh"]-monthly["covered_hh"]),2)
        monthly["demand_before_week_count"]=max(
            0,
            monthly["pmp_count"]-monthly["covered_count_base"],
        )
        monthly["demand_before_week_hh"]=round(max(
            0.0,
            monthly["pmp_hh"]-monthly["covered_hh_base"],
        ),2)
        weekly_target=float(header["hh_objetivo"] or 0)
        monthly["suggested_week_hh"]=round(min(
            weekly_target,
            monthly["demand_before_week_hh"],
        ),2)
        monthly["coverage_possible_pct"]=round(
            min(100.0,weekly_target/monthly["demand_before_week_hh"]*100.0),
            1,
        ) if monthly["demand_before_week_hh"]>0 else 100.0
        monthly["free_preventive_hh"]=round(max(
            0.0,
            weekly_target-monthly["suggested_week_hh"],
        ),2)
        header=dict(header)
        header["monthly_demand"]=monthly
    return header,rows


def export_weekly_excel(programming_id:int)->tuple[bytes,str]:
    import base64
    from pathlib import Path

    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    header,rows=_report_data(programming_id)

    wb=Workbook()
    ws=wb.active
    ws.title="Programación semanal"
    ws.sheet_view.showGridLines=False
    ws.freeze_panes="A16"
    ws.sheet_properties.tabColor="009B5A"
    ws.page_setup.orientation="landscape"
    ws.page_setup.fitToWidth=1
    ws.page_setup.fitToHeight=0
    ws.sheet_properties.pageSetUpPr.fitToPage=True
    ws.page_margins.left=0.25
    ws.page_margins.right=0.25
    ws.page_margins.top=0.35
    ws.page_margins.bottom=0.35

    team_green="009B5A"
    team_dark="007C49"
    team_lime="55C42F"
    team_yellow="F4C20D"
    team_pale="EFF9F3"
    team_yellow_pale="FFF8D9"
    dark="173B31"
    navy="17365D"
    gray="66776F"
    white="FFFFFF"
    border_color="D6E5DC"
    thin=Side(style="thin",color=border_color)

    hh_raw=float(header["hh_disponibles"] or 0)
    hh_effective=round(hh_raw*0.80,2)
    hh_target=float(header["hh_objetivo"] or 0)
    hh_programmed=float(header["hh_programadas"] or 0)
    hh_reserve=float(header["hh_reserva"] or 0)
    items=int(header["items"] or 0)
    specialty_name={
        "MEC":"MECÁNICA",
        "ELE":"ELÉCTRICA",
        "MET":"METROLOGÍA",
        "SER":"SERVICIOS",
    }.get(str(header["especialidad"] or "").upper(),str(header["especialidad"] or ""))

    # Cabecera corporativa.
    ws.merge_cells("C1:I2")
    ws["C1"]="PROGRAMACIÓN SEMANAL DE MANTENIMIENTO"
    ws["C1"].font=Font(size=19,bold=True,color=dark)
    ws["C1"].alignment=Alignment(horizontal="left",vertical="center")

    ws.merge_cells("J1:L1")
    ws["J1"]="CEK GLOBAL"
    ws["J1"].font=Font(size=13,bold=True,color=navy)
    ws["J1"].alignment=Alignment(horizontal="right",vertical="bottom")
    ws.merge_cells("J2:L2")
    ws["J2"]="Inspection Services"
    ws["J2"].font=Font(size=8,bold=True,color=gray)
    ws["J2"].alignment=Alignment(horizontal="right",vertical="top")

    ws.merge_cells("C3:I3")
    ws["C3"]=f"Planta Barranquilla  ·  {specialty_name}  ·  Semana {header['semana_inicio']:%d/%m/%Y} al {header['semana_fin']:%d/%m/%Y}"
    ws["C3"].font=Font(size=9,bold=True,color=gray)
    ws["C3"].alignment=Alignment(horizontal="left",vertical="center")

    ws.merge_cells("J3:L3")
    ws["J3"]=f"Estado: {str(header.get('estado') or 'GUARDADA').upper()}"
    ws["J3"].font=Font(size=8,bold=True,color=team_dark)
    ws["J3"].alignment=Alignment(horizontal="right",vertical="center")

    for col in range(1,13):
        ws.cell(4,col).fill=PatternFill("solid",fgColor=team_green if col<=8 else (team_lime if col<=10 else team_yellow))
    ws.row_dimensions[1].height=30
    ws.row_dimensions[2].height=25
    ws.row_dimensions[3].height=22
    ws.row_dimensions[4].height=5

    # Logo Team Foods.
    try:
        logo_path=Path(__file__).resolve().parents[1]/"assets"/"team_foods_logo.b64"
        logo_bytes=base64.b64decode(logo_path.read_text(encoding="utf-8").strip())
        logo_stream=BytesIO(logo_bytes)
        logo=XLImage(logo_stream)
        logo.width=165
        logo.height=64
        ws.add_image(logo,"A1")
    except Exception:
        ws.merge_cells("A1:B3")
        ws["A1"]="TEAM\nFOODS"
        ws["A1"].font=Font(size=18,bold=True,color=team_green)
        ws["A1"].alignment=Alignment(horizontal="left",vertical="center",wrap_text=True)

    # Tarjetas KPI en colores Team Foods.
    cards=[
        ("A5:B5","A6:B7","H-H BRUTAS",hh_raw,team_green,team_pale),
        ("C5:D5","C6:D7","H-H EFECTIVAS",hh_effective,team_green,team_pale),
        ("E5:F5","E6:F7","META PREVENTIVO",hh_target,team_yellow,team_yellow_pale),
        ("G5:H5","G6:H7","H-H PROGRAMADAS",hh_programmed,team_lime,team_pale),
        ("I5:J5","I6:J7","RESERVA CORRECTIVO",hh_reserve,team_green,team_pale),
        ("K5:L5","K6:L7","ACTIVIDADES",items,team_yellow,team_yellow_pale),
    ]
    for title_range,value_range,label,value,accent,value_fill in cards:
        ws.merge_cells(title_range)
        ws.merge_cells(value_range)
        tc=ws[title_range.split(":")[0]]
        vc=ws[value_range.split(":")[0]]
        tc.value=label
        tc.font=Font(size=8,bold=True,color=white)
        tc.fill=PatternFill("solid",fgColor=accent)
        tc.alignment=Alignment(horizontal="center",vertical="center")
        vc.value=value
        vc.font=Font(size=17,bold=True,color=dark if accent!=team_yellow else navy)
        vc.fill=PatternFill("solid",fgColor=value_fill)
        vc.alignment=Alignment(horizontal="center",vertical="center")
        vc.number_format="0" if isinstance(value,int) else "0.0"
        for row_num in range(ws[title_range.split(":")[0]].row,ws[value_range.split(":")[0]].row+2):
            for col_num in range(ws[title_range.split(":")[0]].column,ws[value_range.split(":")[1]].column+1):
                ws.cell(row_num,col_num).border=Border(left=thin,right=thin,top=thin,bottom=thin)

    ws.merge_cells("A8:L8")
    ws["A8"]="Team Foods · Programación preventiva gestionada por CEK Global Inspection Services"
    ws["A8"].font=Font(size=8,bold=True,color=team_dark)
    ws["A8"].fill=PatternFill("solid",fgColor="F7FBF8")
    ws["A8"].alignment=Alignment(horizontal="left",vertical="center")

    ws.merge_cells("A9:L9")
    ws["A9"]="Criterio: H-H brutas × 80% = H-H efectivas. De las H-H efectivas, 80% se destina a preventivo y 20% a correctivo/reserva. El 20% inicial contempla alistamiento y tiempos operativos."
    ws["A9"].font=Font(size=7.5,italic=True,color=gray)
    ws["A9"].alignment=Alignment(horizontal="left",vertical="center",wrap_text=True)
    ws.row_dimensions[9].height=24

    monthly=header.get("monthly_demand") or {}
    ws.merge_cells("A10:L10")
    ws["A10"]="DEMANDA DEL MES · PMP VS CAPACIDAD SEMANAL"
    ws["A10"].font=Font(size=9,bold=True,color=white)
    ws["A10"].fill=PatternFill("solid",fgColor=team_dark)
    ws["A10"].alignment=Alignment(horizontal="left",vertical="center")
    ws.row_dimensions[10].height=20

    month_cards=[
        ("A11:B11","A12:B13","PMP DEL MES",int(monthly.get("pmp_count") or 0),team_green,team_pale),
        ("C11:D11","C12:D13","H-H PMP DEL MES",float(monthly.get("pmp_hh") or 0),team_green,team_pale),
        ("E11:F11","E12:F13","PMP CUBIERTOS",int(monthly.get("covered_count") or 0),team_lime,team_pale),
        ("G11:H11","G12:H13","H-H CUBIERTAS",float(monthly.get("covered_hh") or 0),team_lime,team_pale),
        ("I11:J11","I12:J13","PMP PENDIENTES",int(monthly.get("pending_count") or 0),team_yellow,team_yellow_pale),
        ("K11:L11","K12:L13","H-H PENDIENTES",float(monthly.get("pending_hh") or 0),team_yellow,team_yellow_pale),
    ]
    for title_range,value_range,label,value,accent,value_fill in month_cards:
        ws.merge_cells(title_range)
        ws.merge_cells(value_range)
        tc=ws[title_range.split(":")[0]]
        vc=ws[value_range.split(":")[0]]
        tc.value=label
        tc.font=Font(size=7.5,bold=True,color=white)
        tc.fill=PatternFill("solid",fgColor=accent)
        tc.alignment=Alignment(horizontal="center",vertical="center")
        vc.value=value
        vc.font=Font(size=15,bold=True,color=dark if accent!=team_yellow else navy)
        vc.fill=PatternFill("solid",fgColor=value_fill)
        vc.alignment=Alignment(horizontal="center",vertical="center")
        vc.number_format="0" if isinstance(value,int) else "0.0"
        for row_num in range(ws[title_range.split(":")[0]].row,ws[value_range.split(":")[0]].row+2):
            for col_num in range(ws[title_range.split(":")[0]].column,ws[value_range.split(":")[1]].column+1):
                ws.cell(row_num,col_num).border=Border(left=thin,right=thin,top=thin,bottom=thin)

    demand_before=float(monthly.get("demand_before_week_hh") or 0)
    suggested=float(monthly.get("suggested_week_hh") or 0)
    coverage=float(monthly.get("coverage_possible_pct") or 0)
    free_capacity=float(monthly.get("free_preventive_hh") or 0)
    ws.merge_cells("A14:L14")
    if demand_before<=0:
        comparison_text="El PMP mensual ya se encuentra cubierto. La capacidad preventiva semanal puede destinarse a backlog u otros trabajos preventivos."
    elif weekly_target>=demand_before:
        comparison_text=(
            f"CAPACIDAD SEMANAL SUFICIENTE · Meta preventiva: {weekly_target:.1f} H-H · "
            f"Demanda pendiente antes de esta semana: {demand_before:.1f} H-H · "
            f"Objetivo sugerido: {suggested:.1f} H-H · Capacidad preventiva libre: {free_capacity:.1f} H-H"
        )
    else:
        comparison_text=(
            f"COBERTURA PARCIAL · Meta preventiva: {weekly_target:.1f} H-H · "
            f"Demanda pendiente antes de esta semana: {demand_before:.1f} H-H · "
            f"Cobertura posible esta semana: {coverage:.1f}%"
        )
    ws["A14"]=comparison_text
    ws["A14"].font=Font(size=8,bold=True,color=team_dark)
    ws["A14"].fill=PatternFill("solid",fgColor="F7FBF8")
    ws["A14"].alignment=Alignment(horizontal="left",vertical="center",wrap_text=True)
    ws["A14"].border=Border(left=thin,right=thin,top=thin,bottom=thin)
    ws.row_dimensions[14].height=28

    headers=["OT","Área","Criticidad","Código equipo","Descripción equipo","Plan de trabajo","Condición","Origen","Personas","Tiempo min","H-H","Grupo"]
    for col,label in enumerate(headers,1):
        c=ws.cell(15,col,label)
        c.font=Font(bold=True,color=white,size=8.5)
        c.fill=PatternFill("solid",fgColor=team_dark)
        c.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
        c.border=Border(left=thin,right=thin,top=thin,bottom=thin)
    ws.row_dimensions[15].height=26

    for idx,row in enumerate(rows,16):
        origin="BACKLOG" if str(row.get("origen") or "").upper()=="BACKLOG" else "PMP DEL MES"
        vals=[
            row.get("numero_ot") or "SIN ASIGNAR",
            row.get("area_nombre") or row.get("area_codigo") or "",
            row.get("criticidad") or "",
            row.get("activo_codigo") or "",
            row.get("activo_descripcion") or "",
            row.get("plan_trabajo") or "",
            row.get("condicion") or "",
            origin,
            float(row["personas"]) if row.get("personas") is not None else "",
            float(row["tiempo_min"]) if row.get("tiempo_min") is not None else "",
            float(row["hh_programadas"]) if row.get("hh_programadas") is not None else "",
            row.get("descripcion_grupo") or "",
        ]
        base_fill="FFFFFF" if idx%2 else "F8FBF9"
        if origin=="BACKLOG":
            base_fill="FFF8D9"
        for col,value in enumerate(vals,1):
            c=ws.cell(idx,col,value)
            c.font=Font(size=8,color=dark)
            c.fill=PatternFill("solid",fgColor=base_fill)
            c.alignment=Alignment(vertical="top",wrap_text=True,horizontal="center" if col in (3,8,9,10,11) else "left")
            c.border=Border(left=thin,right=thin,top=thin,bottom=thin)

        condition_cell=ws.cell(idx,7)
        if bool(row.get("requiere_parada")):
            condition_cell.fill=PatternFill("solid",fgColor=team_yellow_pale)
            condition_cell.font=Font(size=8,bold=True,color="7A5B00")
        else:
            condition_cell.fill=PatternFill("solid",fgColor=team_pale)
            condition_cell.font=Font(size=8,bold=True,color=team_dark)

        origin_cell=ws.cell(idx,8)
        origin_cell.font=Font(size=8,bold=True,color="7A5B00" if origin=="BACKLOG" else team_dark)

    widths=[16,24,11,20,34,40,21,15,10,12,10,25]
    for i,w in enumerate(widths,1):
        ws.column_dimensions[get_column_letter(i)].width=w

    last_row=max(15,15+len(rows))
    ws.auto_filter.ref=f"A15:L{last_row}"
    ws.print_title_rows="1:15"
    ws.print_area=f"A1:L{last_row}"
    ws.oddFooter.left.text="Team Foods · CEK Global Inspection Services"
    ws.oddFooter.left.size=8
    ws.oddFooter.right.text="Página &P de &N"
    ws.oddFooter.right.size=8

    out=BytesIO()
    wb.save(out)
    out.seek(0)
    return out.getvalue(),f"programacion_{header['especialidad']}_{header['semana_inicio']:%Y%m%d}_{header['semana_fin']:%Y%m%d}.xlsx"


def export_weekly_pdf(programming_id:int)->tuple[bytes,str]:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    header,rows=_report_data(programming_id);out=BytesIO();doc=SimpleDocTemplate(out,pagesize=landscape(A4),leftMargin=8*mm,rightMargin=8*mm,topMargin=8*mm,bottomMargin=8*mm,title="Programación semanal de mantenimiento")
    styles=getSampleStyleSheet();title_style=ParagraphStyle("Title2",parent=styles["Heading1"],fontName="Helvetica-Bold",fontSize=15,leading=18,textColor=colors.HexColor("#17365D"),alignment=TA_CENTER);sub_style=ParagraphStyle("Sub2",parent=styles["Normal"],fontSize=8,leading=10,textColor=colors.HexColor("#4B5563"),alignment=TA_CENTER);cell=ParagraphStyle("Cell2",parent=styles["Normal"],fontSize=5.8,leading=7);cell_center=ParagraphStyle("CellCenter2",parent=cell,alignment=TA_CENTER);bold=ParagraphStyle("Bold2",parent=cell,fontName="Helvetica-Bold")
    story=[Paragraph("PROGRAMACIÓN SEMANAL DE MANTENIMIENTO",title_style),Paragraph(f"Semana {header['semana_inicio']:%d/%m/%Y} al {header['semana_fin']:%d/%m/%Y} &nbsp;|&nbsp; Especialidad: <b>{header['especialidad']}</b>",sub_style),Spacer(1,3*mm)]
    summary=[[Paragraph("H-H BRUTAS",bold),Paragraph("META PREVENTIVO",bold),Paragraph("H-H PROGRAMADAS",bold),Paragraph("RESERVA CORRECTIVO",bold),Paragraph("ACTIVIDADES",bold)],[f"{float(header['hh_disponibles'] or 0):.1f}",f"{float(header['hh_objetivo'] or 0):.1f}",f"{float(header['hh_programadas'] or 0):.1f}",f"{float(header['hh_reserva'] or 0):.1f}",str(int(header['items'] or 0))]]
    st=Table(summary,colWidths=[52*mm]*5,rowHeights=[7*mm,8*mm]);st.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#F3F6FA")),("BACKGROUND",(0,1),(-1,1),colors.HexColor("#D9EAF7")),("TEXTCOLOR",(0,0),(-1,-1),colors.HexColor("#17365D")),("FONTNAME",(0,1),(-1,1),"Helvetica-Bold"),("FONTSIZE",(0,1),(-1,1),12),("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#C9D6E3"))]));story.extend([st,Spacer(1,2*mm),Paragraph("Criterio: 80% de las H-H brutas se consideran H-H efectivas; el 20% inicial corresponde a alistamiento y otros tiempos operativos. De las H-H efectivas se reserva 80% para preventivo y 20% para correctivo/reserva.",sub_style),Spacer(1,4*mm)])
    def pp(v,style=cell):return Paragraph(escape(str(v or "")),style)
    data=[[pp(x,bold) for x in ["OT","Área","Equipo","Descripción","Plan de trabajo","Condición","Pers.","Min","H-H"]]]
    for row in rows:data.append([pp(row.get("numero_ot") or "SIN ASIGNAR",cell_center),pp(row.get("area_nombre") or row.get("area_codigo")),pp(row.get("activo_codigo")),pp(row.get("activo_descripcion")),pp(row.get("plan_trabajo")),pp(row.get("condicion")),pp("" if row.get("personas") is None else f"{float(row['personas']):.0f}",cell_center),pp("" if row.get("tiempo_min") is None else f"{float(row['tiempo_min']):.0f}",cell_center),pp("" if row.get("hh_programadas") is None else f"{float(row['hh_programadas']):.1f}",cell_center)])
    table=Table(data,colWidths=[24*mm,28*mm,27*mm,44*mm,55*mm,30*mm,10*mm,12*mm,12*mm],repeatRows=1);table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#2F75B5")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("VALIGN",(0,0),(-1,-1),"TOP"),("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#D9E2F3")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F8FAFC")]),("LEFTPADDING",(0,0),(-1,-1),2.5),("RIGHTPADDING",(0,0),(-1,-1),2.5),("TOPPADDING",(0,0),(-1,-1),2.5),("BOTTOMPADDING",(0,0),(-1,-1),2.5)]));story.append(table);doc.build(story);out.seek(0)
    return out.getvalue(),f"programacion_{header['especialidad']}_{header['semana_inicio']:%Y%m%d}_{header['semana_fin']:%Y%m%d}.pdf"
