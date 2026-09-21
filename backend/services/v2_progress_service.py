from __future__ import annotations

from collections import defaultdict
from datetime import date
from html import escape
from io import BytesIO
from typing import Any

from sqlalchemy import text
from backend.database import get_engine

SPECS = {"MEC": "Mecánica", "ELE": "Eléctrica", "MET": "Metrología", "SER": "Servicios"}


def _period(year: int, month: int) -> tuple[date, date]:
    if not 2020 <= year <= 2100 or not 1 <= month <= 12:
        raise ValueError("Periodo inválido")
    begin = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return begin, end


def _pct(a: float, b: float) -> float:
    return round(100 * a / b, 1) if b else 0.0


def aggregate_progress(headers: list[dict[str, Any]], items: list[dict[str, Any]],
                       pmp_count: int) -> dict[str, Any]:
    """Semana = ejecuciones programadas; mes = OT únicas con último cierre conocido."""
    by_week: dict[int, dict[str, Any]] = {}
    for row in headers:
        week = dict(row)
        week.update({
            "programming_id": int(row["id"]),
            "programmed": 0, "finalized": 0, "pending": 0,
            "not_found": 0, "unchecked": 0,
            "hh_programmed": 0.0, "hh_finalized": 0.0,
            "hh_pending": 0.0, "hh_not_found": 0.0,
            "origin_backlog": 0, "progress_ot_pct": 0.0,
            "progress_hh_pct": 0.0,
        })
        week["week_from"] = str(row["semana_inicio"])
        week["week_to"] = str(row["semana_fin"])
        by_week[int(row["id"])] = week

    latest: dict[int, dict[str, Any]] = {}
    for item in items:
        week = by_week.get(int(item["programacion_id"]))
        if not week:
            continue
        hh = float(item["hh_programadas"] or 0)
        week["programmed"] += 1
        week["hh_programmed"] += hh
        if item.get("origen_backlog"):
            week["origin_backlog"] += 1
        # Una programación GUARDADA todavía no equivale a una OT finalizada o pendiente.
        if week["estado"] == "CERRADA" and item.get("estado_cierre"):
            if item["finalizado"] is True:
                week["finalized"] += 1
                week["hh_finalized"] += hh
            elif item["finalizado"] is False:
                week["pending"] += 1
                week["hh_pending"] += hh
            else:
                week["not_found"] += 1
                week["hh_not_found"] += hh
        else:
            week["unchecked"] += 1
        oid = int(item["orden_mantenimiento_id"])
        priority = (week["semana_fin"], week["semana_inicio"], int(week["id"]))
        previous = latest.get(oid)
        if not previous or priority > previous["_priority"]:
            latest[oid] = {**item, "_priority": priority, "_estado_programacion": week["estado"]}

    weeks = sorted(by_week.values(), key=lambda w: (w["semana_inicio"], w["especialidad"]))
    totals = {key: 0 for key in (
        "programmed", "finalized", "pending", "not_found", "unchecked",
        "origin_backlog", "hh_programmed", "hh_finalized", "hh_pending", "hh_not_found",
    )}
    specialty_agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {**{key: 0 for key in totals}, "closed": 0, "weeks": 0}
    )
    for week in weeks:
        week["progress_ot_pct"] = _pct(week["finalized"], week["programmed"]) if week["estado"] == "CERRADA" else None
        week["progress_hh_pct"] = _pct(week["hh_finalized"], week["hh_programmed"]) if week["estado"] == "CERRADA" else None
        for key in totals:
            if key.startswith("hh_"):
                week[key] = round(week[key], 2)
            totals[key] += week[key]
            specialty_agg[week["especialidad"]][key] += week[key]
        specialty_agg[week["especialidad"]]["weeks"] += 1
        specialty_agg[week["especialidad"]]["closed"] += int(week["estado"] == "CERRADA")
    for key in totals:
        if key.startswith("hh_"):
            totals[key] = round(totals[key], 2)

    unique = {"programmed": len(latest), "finalized": 0, "pending": 0,
              "not_found": 0, "unchecked": 0}
    unresolved = []
    for record in latest.values():
        status = record["_estado_programacion"]
        if status != "CERRADA" or not record.get("estado_cierre"):
            unique["unchecked"] += 1
        elif record["finalizado"] is True:
            unique["finalized"] += 1
        elif record["finalizado"] is False:
            unique["pending"] += 1
        else:
            unique["not_found"] += 1
        if status == "CERRADA" and record["finalizado"] is not True:
            unresolved.append({
                "numero_ot": record.get("numero_ot") or "SIN ASIGNAR",
                "activo": record.get("activo_codigo") or "",
                "plan": record.get("plan_clave_software") or "",
                "especialidad": record.get("especialidad") or "",
                "estado_cierre": record.get("estado_cierre") or "SIN VERIFICAR",
                "hh_estimada": round(float(record.get("hh_programadas") or 0), 2),
                "resultado": "PENDIENTE" if record["finalizado"] is False else "NO ENCONTRADA",
            })
    unresolved.sort(key=lambda row: (row["especialidad"], row["resultado"], row["numero_ot"]))
    for code, record in specialty_agg.items():
        record["especialidad"] = code
        record["name"] = SPECS.get(code, code)
        for key in totals:
            if key.startswith("hh_"):
                record[key] = round(record[key], 2)
        record["progress_ot_pct"] = _pct(record["finalized"], record["programmed"])
        record["progress_hh_pct"] = _pct(record["hh_finalized"], record["hh_programmed"])

    unique["progress_ot_pct"] = _pct(unique["finalized"], unique["programmed"])
    complete = bool(weeks) and all(w["estado"] == "CERRADA" for w in weeks)
    return {
        "weeks": weeks, "specialties": sorted(specialty_agg.values(), key=lambda x: x["especialidad"]),
        "weekly_totals": {**totals, "progress_ot_pct": _pct(totals["finalized"], totals["programmed"]),
                          "progress_hh_pct": _pct(totals["hh_finalized"], totals["hh_programmed"])},
        "monthly": {**unique, "pmp_count": int(pmp_count),
                    "not_programmed": max(0, int(pmp_count) - unique["programmed"]),
                    "all_weeks_closed": complete, "weeks_total": len(weeks),
                    "weeks_closed": sum(w["estado"] == "CERRADA" for w in weeks)},
        "unresolved": unresolved,
        "criteria": {
            "weekly": "Cada OT se cuenta por cada semana programada; solo CERRADA tiene resultado de ejecución.",
            "monthly": "Cada OT se cuenta una vez según el cierre de su última semana programada del periodo.",
            "hh": "H-H estimadas al programar, NO horas reales trabajadas.",
            "month": "Semanas cuya fecha de inicio pertenece al mes seleccionado; OPERACIÓN excluida.",
            "pmp": "Cartera PMP de mantenimiento del mes, aunque alguna OT nunca haya sido programada.",
        },
    }


def get_progress(year: int, month: int) -> dict[str, Any]:
    begin, end = _period(year, month)
    with get_engine().connect() as conn:
        headers = [dict(r) for r in conn.execute(text("""
            SELECT id,semana_inicio,semana_fin,especialidad,estado,
                   hh_disponibles,hh_objetivo,hh_reserva,cierre_en,cierre_archivo
            FROM programacion.programacion_semanal_v2
            WHERE semana_inicio >= :begin AND semana_inicio < :end
            ORDER BY semana_inicio,especialidad
        """), {"begin": begin, "end": end}).mappings()]
        items = [dict(r) for r in conn.execute(text("""
            SELECT i.programacion_id,i.orden_mantenimiento_id,i.hh_programadas,
                   i.finalizado,i.estado_cierre,i.origen_backlog,
                   o.numero_ot,o.plan_clave_software,o.especialidad,
                   a.codigo AS activo_codigo
            FROM programacion.programacion_item_v2 i
            JOIN programacion.programacion_semanal_v2 s ON s.id=i.programacion_id
            JOIN programacion.orden_mantenimiento o ON o.id=i.orden_mantenimiento_id
            JOIN programacion.activo a ON a.id=o.activo_id
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE s.semana_inicio >= :begin AND s.semana_inicio < :end
              AND COALESCE(p.es_operacion,false)=false
        """), {"begin": begin, "end": end}).mappings()]
        pmp_count = conn.execute(text("""
            SELECT count(*) FROM programacion.orden_mantenimiento o
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.periodo=:begin AND COALESCE(p.es_operacion,false)=false
        """), {"begin": begin}).scalar_one()
    return {"year": year, "month": month, **aggregate_progress(headers, items, pmp_count)}


def export_progress_pdf(year: int, month: int, programming_id: int | None = None) -> tuple[bytes, str]:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.graphics.shapes import Drawing, Rect, String

    data = get_progress(year, month)
    weeks = data["weeks"]
    kind = "mensual"
    if programming_id is not None:
        weeks = [w for w in weeks if w["programming_id"] == programming_id]
        if not weeks:
            raise ValueError("La programación no corresponde al mes indicado")
        kind = "semanal"
    if not weeks:
        raise ValueError("No hay programaciones para generar el reporte")
    if kind == "mensual":
        summary = data["weekly_totals"]
        title = "INFORME MENSUAL DE MANTENIMIENTO"
        subtitle = f"Periodo {year}-{month:02d} | {data['monthly']['weeks_closed']} de {data['monthly']['weeks_total']} cierres"
    else:
        summary = weeks[0]
        title = "INFORME DE CIERRE SEMANAL"
        subtitle = f"{weeks[0]['week_from']} al {weeks[0]['week_to']} | {SPECS.get(weeks[0]['especialidad'],weeks[0]['especialidad'])}"
    navy = colors.HexColor("#17365D")
    blue = colors.HexColor("#2F75B5")
    pale = colors.HexColor("#E9F2FA")
    dark = colors.HexColor("#253447")
    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=landscape(A4), leftMargin=14*mm,
        rightMargin=14*mm, topMargin=12*mm, bottomMargin=12*mm, title=title)
    styles = getSampleStyleSheet()
    big = ParagraphStyle("CEKTitle", parent=styles["Heading1"], fontSize=17, leading=21,
                         textColor=navy, alignment=TA_CENTER)
    centered = ParagraphStyle("CEKSub", parent=styles["Normal"], fontSize=9, leading=12,
                              alignment=TA_CENTER, textColor=dark)
    cell = ParagraphStyle("CEKCell", parent=styles["Normal"], fontSize=7.1, leading=9)
    small = ParagraphStyle("CEKSmall", parent=styles["Normal"], fontSize=8, leading=11)
    bold = ParagraphStyle("CEKBold", parent=cell, fontName="Helvetica-Bold")
    def para(value: Any, style=cell):
        return Paragraph(escape(str(value if value is not None else "")), style)
    def styled_table(rows, widths, header=True):
        table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="CENTER")
        commands = [("VALIGN",(0,0),(-1,-1),"TOP"),
                    ("LINEBELOW",(0,0),(-1,-1),.25,colors.HexColor("#C6D5E4")),
                    ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
                    ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]
        if header:
            commands += [("BACKGROUND",(0,0),(-1,0),blue),
                         ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                         ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,pale])]
        table.setStyle(TableStyle(commands))
        return table
    story = [
        para("TEAM FOODS · C.E.K GLOBAL INSPECTION", centered), Spacer(1,2*mm),
        Paragraph(title,big),para(subtitle,centered), Spacer(1,7*mm),
    ]
    metrics = [
        ("OT PROGRAMADAS", summary["programmed"]), ("FINALIZADAS", summary["finalized"]),
        ("PENDIENTES", summary["pending"]), ("NO ENCONTRADAS", summary["not_found"]),
        ("H-H PROGRAMADAS", f"{summary['hh_programmed']:.2f}"),
        ("H-H DE OT CERRADAS", f"{summary['hh_finalized']:.2f}"),
    ]
    story.append(styled_table([
        [para(label,bold) for label,_ in metrics],
        [para(value,bold) for _,value in metrics],
    ], [43*mm]*6, False))
    story += [Spacer(1,5*mm),para(
        f"Cumplimiento por OT (eventos semanales): {summary['progress_ot_pct'] or 0:.1f}%   |   "
        f"Cumplimiento por HH estimadas: {summary['progress_hh_pct'] or 0:.1f}%",small),
        Spacer(1,5*mm)]
    if kind == "mensual":
        m = data["monthly"]
        story.append(para(
            f"CONSOLIDADO SIN DUPLICADOS: {m['programmed']} OT distintas programadas; "
            f"{m['finalized']} finalizadas; {m['pending']} pendientes; "
            f"{m['not_found']} no encontradas; {m['unchecked']} sin verificar. "
            f"PMP del mes: {m['pmp_count']} registros de mantenimiento. "
            f"Sin programación del periodo: {m['not_programmed']}.",small))
        story.append(Spacer(1,4*mm))
        if not m["all_weeks_closed"]:
            story.append(para("INFORME PARCIAL: aún existen semanas no cerradas.",small))
            story.append(Spacer(1,3*mm))
    title_row = ["Semana","Esp.","Estado","OT prog.","Final.","Pend.","No enc.","HH prog.","HH final.","OT %","HH %"]
    data_rows = [[para(x,bold) for x in title_row]]
    for w in weeks:
        data_rows.append([para(v) for v in [
            f"{w['week_from'][5:]} a {w['week_to'][5:]}",
            w["especialidad"],w["estado"],w["programmed"],w["finalized"],w["pending"],
            w["not_found"],f"{w['hh_programmed']:.1f}",f"{w['hh_finalized']:.1f}",
            "-" if w["progress_ot_pct"] is None else f"{w['progress_ot_pct']:.1f}%",
            "-" if w["progress_hh_pct"] is None else f"{w['progress_hh_pct']:.1f}%"
        ]])
    story.append(styled_table(data_rows,[28*mm,14*mm,20*mm,18*mm,16*mm,16*mm,17*mm,22*mm,22*mm,17*mm,17*mm]))
    story.append(Spacer(1,5*mm))
    drawing = Drawing(650,75)
    max_programmed = max((int(w["programmed"]) for w in weeks),default=1) or 1
    for i,w in enumerate(weeks[:15]):
        x=10+i*43
        h=47*int(w["programmed"])/max_programmed
        f=47*int(w["finalized"])/max_programmed
        drawing.add(Rect(x,17,15,h,fillColor=colors.HexColor("#C7D9E8"),strokeColor=None))
        drawing.add(Rect(x+16,17,15,f,fillColor=blue,strokeColor=None))
        drawing.add(String(x,5,str(i+1),fontSize=7,fillColor=dark))
    story.append(drawing)
    story.append(para("Barras: OT programadas (clara) vs finalizadas (azul), en el orden de la tabla.",small))
    story.append(Spacer(1,5*mm))
    story.append(para(
        "CRITERIOS: Las OT y H-H de la tabla semanal son eventos por semana; "
        "una OT reprogramada puede figurar en varias semanas. Las OT del consolidado mensual "
        "se cuentan una sola vez, según el cierre de su última semana del periodo. "
        "Las H-H de OT finalizadas son estimaciones del plan, no horas reales ejecutadas. "
        "Las actividades OPERACIÓN quedan excluidas.", small))
    if kind == "mensual" and data["unresolved"]:
        story += [PageBreak(),para("PENDIENTES DEL ÚLTIMO CIERRE DEL MES",big),
                  para("OT no finalizadas (sin duplicados; últimas semanas del periodo)",centered),
                  Spacer(1,5*mm)]
        cols = ["OT","Esp.","Equipo","Plan","Estado cierre","Resultado","HH est."]
        table_rows = [[para(x,bold) for x in cols]]
        for u in data["unresolved"][:80]:
            table_rows.append([para(v) for v in [
                u["numero_ot"],u["especialidad"],u["activo"],u["plan"],
                u["estado_cierre"],u["resultado"],f"{u['hh_estimada']:.2f}"
            ]])
        story.append(styled_table(table_rows,[30*mm,14*mm,39*mm,75*mm,35*mm,31*mm,20*mm]))
        if len(data["unresolved"])>80:
            story += [Spacer(1,3*mm),para(
                f"Se muestran las primeras 80 de {len(data['unresolved'])} OT pendientes; el tablero conserva el total.",small)]
    doc.build(story)
    return out.getvalue(), (
        f"informe_{kind}_mtto_{year}_{month:02d}"
        + (f"_{programming_id}" if programming_id is not None else "") + ".pdf"
    )
