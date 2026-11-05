"""A4 executive monthly report without external PDF libraries.

Vercel may omit optional ReportLab from a Python function bundle. Never
replace the approved monthly executive document with the legacy 10-page
landscape weekly-style report when that happens.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

from backend.services.v2_pdf_fallback import (
    _PDF, _fmt, _pct, _clip, NAVY, BLUE, SKY, GREEN, MINT, AMBER,
    CREAM, RED, PALE, GRAY, LINE, WHITE, INK, MONTHS, NAMES,
)

TEAL = (.08, .53, .58)
DARK = (.04, .18, .29)
TINT = (.93, .97, .98)
W, H = 595, 842
L, R = 37, 558
PAGE_WIDTH = R - L


def _num(value: Any, decimals: int = 0) -> str:
    return _fmt(value, decimals)


def _n(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.


def _percent(done, total) -> float:
    return round(100 * _n(done) / _n(total), 1) if _n(total) else 0.


def _p(value) -> str:
    return f"{_num(value,1)}%"


def _short(s, length=56):
    return _clip(s, length)


class _PortraitPDF(_PDF):
    W, H = W, H

    def new_page(self):
        if self.parts:
            self.pages.append(b"\n".join(self.parts))
        self.parts = []
        self.page_number += 1
        self.rect(0, 0, W, H, WHITE)
        if self.page_number > 1:
            self.text(R, 816, "C.E.K / TEAM FOODS  |  INFORME GERENCIAL",
                      8, NAVY, True)  # aligned by short length
            self.rule(L, 804, R, 804, LINE)
            self.rule(L, 49, R, 49, LINE)
            self.text(L, 33, "C.E.K GLOBAL INSPECTION  |  MANTENIMIENTO", 7, GRAY)
            self.text(480, 33, f"PAG. {self.page_number} / 7", 8, NAVY, True)
        self.y = 780

    def cover(self, year, month, issue, code, complete):
        self.rect(0, 0, W, H, WHITE)
        self.rect(0, 725, W, 117, NAVY)
        self.rect(0, 719, 352, 13, BLUE)
        self.rect(0, 708, 264, 8, TEAL)
        for x in range(360, 580, 28):
            self.rule(x, 600, x, 835, SKY, .4)
        for y in range(610, 833, 28):
            self.rule(355, y, 595, y, SKY, .4)
        self.rect(143, 572, 310, 135, WHITE, LINE)
        if self.logo_jpeg:
            self.emit("q 130 0 0 130 231 575 cm /Logo Do Q")
        self.text(101, 524, "INFORME GERENCIAL", 30, NAVY, True)
        self.text(126, 486, "DE MANTENIMIENTO", 24, INK, True)
        self.rule(82, 470, 513, 470, TEAL, 3)
        self.text(101, 439, "Consolidado mensual de programación,", 14, NAVY, True)
        self.text(160, 416, "cumplimiento y backlog", 14, NAVY, True)
        self.text(153, 382, "Planta Barranquilla  |  Team Foods", 11, GRAY)
        self.rect(0, 169, W, 192, TINT)
        # Silueta esquemática de una planta de aceite, como elemento visual.
        self.rect(50, 181, 60, 102, WHITE, BLUE)
        self.rect(139, 181, 50, 155, WHITE, BLUE)
        self.rect(214, 181, 75, 118, WHITE, BLUE)
        self.rect(317, 181, 54, 145, WHITE, BLUE)
        self.rect(396, 181, 111, 82, WHITE, BLUE)
        for y in (200, 220, 240, 260):
            self.rule(51, y, 370, y, SKY, 1)
        self.rule(108, 270, 220, 270, BLUE, 2)
        self.rule(286, 253, 394, 253, BLUE, 2)
        self.rect(0, 0, W, 166, NAVY)
        self.text(40, 130, f"{MONTHS[month]} {year}", 21, WHITE, True)
        self.text(40, 103, "Entregable para Team Foods", 11, SKY)
        self.text(40, 78, "C.E.K Global Inspection Services S.A.S.", 9, WHITE, True)
        self.text(40, 55, f"{code}  |  Rev. 00  |  {issue}", 9, SKY)
        self.text(40, 29, "CIERRE CONCILIADO" if complete else
                  "INFORME PARCIAL / PROGRAMACIONES ABIERTAS", 8, SKY, True)
        if self.team_logo_jpeg:
            self.rect(390, 63, 163, 70, WHITE)
            self.emit("q 152 0 0 58 396 69 cm /TeamLogo Do Q")

    def heading(self, number, title, desc):
        self.text(L, 771, f"{number} / INFORME MENSUAL", 9, TEAL, True)
        self.text(L, 735, title, 22, NAVY, True)
        self.write_wrapped(desc, L, 710, 93, 9, GRAY)
        self.rect(L, 678, 102, 4, TEAL)
        self.rect(L+104, 678, PAGE_WIDTH-104, 4, SKY)

    def write_wrapped(self, text, x, y, width_chars=76, size=9,
                      color=INK, line_h=15, max_lines=7, bold=False):
        words = str(text).split()
        line = ""
        for word in words:
            new = f"{line} {word}".strip()
            if len(new) > width_chars and line:
                self.text(x, y, line, size, color, bold)
                y -= line_h
                max_lines -= 1
                if not max_lines:
                    return y
                line = word
            else:
                line = new
        if line and max_lines:
            self.text(x, y, line, size, color, bold)
            y -= line_h
        return y

    def section(self, title, subtitle=None):
        self.text(L, self.y, title.upper(), 10, NAVY, True)
        self.y -= 25
        if subtitle:
            self.y = self.write_wrapped(subtitle, L, self.y,
                                        103, 8, GRAY, 12, 2)
            self.y -= 9

    def block(self, x, y, width, height, name, value, desc="",
              color=BLUE):
        self.rect(x, y, width, height, WHITE, LINE)
        self.rect(x, y + height - 5, width, 5, color)
        self.text(x+10, y+height-25, name.upper(), 8, GRAY, True)
        self.text(x+10, y+height-57, str(value), 22, color, True)
        if desc:
            self.write_wrapped(desc, x+10, y+14, max(12,int((width-20)/4.3)),
                               7.3, GRAY, 10, 2)

    def simple_table(self, headers, rows, widths, y, height=29, body_size=8,
                     limit=10):
        total = sum(widths)
        self.rect(L, y-30, total, 30, NAVY)
        x=L
        for h, w in zip(headers,widths):
            self.text(x+5,y-19,_short(h, max(4,int((w-8)/4.1))),7.3,WHITE,True)
            x+=w
        top=y-30
        for k,row in enumerate(rows[:limit]):
            yy=top-(k+1)*height
            if yy < 70:
                break
            self.rect(L,yy,total,height,PALE if k%2==0 else WHITE)
            xx=L
            for v,w in zip(row,widths):
                self.text(xx+5, yy+10,
                          _short(v,max(3,int((w-9)/(body_size*.5)))),
                          body_size,INK)
                xx+=w
            self.rule(L,yy,L+total,yy,LINE,.35)
        return top-min(len(rows),limit)*height


def _metrics(data):
    month = data.get("monthly") or {}
    specs = data.get("monthly_progress_by_specialty") or []
    if specs:
        total=sum(_n(s.get("total_ot")) for s in specs)
        done=sum(_n(s.get("completed_ot")) for s in specs)
        plan=sum(_n(s.get("scheduled_unique")) for s in specs)
        plan_done=sum(_n(s.get("scheduled_completed")) for s in specs)
        unplanned=sum(_n(s.get("unplanned_completed")) for s in specs)
        hours=sum(_n(s.get("total_hh")) for s in specs)
        hours_done=sum(_n(s.get("completed_hh")) for s in specs)
        extras=sum(_n(s.get("scheduled_reprogrammed_assignments")) for s in specs)
    else:
        # Compatible with older snapshots lacking the newer specialty KPI.
        total=_n(month.get("programmed"))
        done=_n(month.get("finalized"))
        plan=total;plan_done=done;unplanned=0
        hours=_n((data.get("weekly_totals") or {}).get("hh_programmed"))
        hours_done=_n((data.get("weekly_totals") or {}).get("hh_finalized"))
        extras=0
    return dict(month=month,specs=specs,total=int(total),done=int(done),
                plan=int(plan),plan_done=int(plan_done),unplanned=int(unplanned),
                hours=hours,hours_done=hours_done,extras=int(extras),
                general_pct=_percent(done,total),
                planned_pct=_percent(plan_done,plan),
                complete=bool(month.get("all_weeks_closed")))


def _week_groups(data):
    out=defaultdict(lambda:dict(assigned=0,done=0,closed=True))
    for w in data.get("weeks") or []:
        key=(str(w.get("week_from") or "")[:10],str(w.get("week_to") or "")[:10])
        row=out[key]
        row["assigned"]+=int(_n(w.get("programmed")))
        row["done"]+=int(_n(w.get("finalized")))
        row["closed"]=row["closed"] and w.get("estado")=="CERRADA"
    return sorted(out.items())


def render_monthly_executive_vector(data:dict[str,Any],year:int,month:int):
    if not data.get("weeks"):
        raise ValueError("No hay programaciones para generar el reporte")
    m=_metrics(data)
    issue=datetime.now(ZoneInfo("America/Bogota")).strftime("%d/%m/%Y")
    code=f"CEK-MTTO-{year}-{month:02d}"
    pdf=_PortraitPDF("INFORME GERENCIAL", f"{MONTHS[month]} {year}", "MENSUAL")
    pdf.cover(year,month,issue,code,m["complete"])

    # 02. Resumen ejecutivo.
    pdf.new_page()
    pdf.heading("01","Resumen ejecutivo","Cartera mensual de mantenimiento  |  Planta Barranquilla")
    xgap=10; cw=(PAGE_WIDTH-2*xgap)/3
    pdf.text(L,648,"ALCANCE EN CIFRAS",11,NAVY,True)
    for i,(label,val,detail,color) in enumerate((
        ("OT en cartera",_num(m["total"]),"PMP y backlog",NAVY),
        ("OT finalizadas",_num(m["done"]),"Dentro y fuera del plan",TEAL),
        ("Cumplimiento general",_p(m["general_pct"]),"OT únicas del mes",BLUE))):
        pdf.block(L+i*(cw+xgap),524,cw,97,label,val,detail,color)
    pdf.text(L,488,"RESULTADOS DE LA EJECUCION",11,NAVY,True)
    for i,(label,val,detail,color) in enumerate((
        ("OT programadas únicas",_num(m["plan"]),"Sin reprogramaciones",NAVY),
        ("H-H OT finalizadas",_num(m["hours_done"],1),
         f"De {_num(m['hours'],1)} H-H estimadas",TEAL),
        ("Fuera de programación",_num(m["unplanned"]),
         "OT únicas finalizadas",AMBER))):
        pdf.block(L+i*(cw+xgap),363,cw,97,label,val,detail,color)
    pdf.text(L,331,"LECTURA GERENCIAL",11,NAVY,True)
    pdf.rect(L,193,PAGE_WIDTH,115,PALE,LINE)
    narrative=(f"Se identificaron {_num(m['total'])} OT únicas de la cartera del mes; "
               f"{_num(m['done'])} cuentan con finalización acreditada, "
               f"equivalentes a {_p(m['general_pct'])} de cumplimiento. "
               f"De ellas, {_num(m['plan_done'])} fueron programadas y "
               f"{_num(m['unplanned'])} se finalizaron fuera de programación.")
    pdf.write_wrapped(narrative,L+14,280,91,10,INK,16,5)
    pdf.text(L,166,"CRITERIOS DE INTERPRETACION",10,NAVY,True)
    pdf.write_wrapped("La cartera contiene órdenes PMP y backlog. Cada OT se cuenta una "
                      "sola vez aunque se reprograme. Las H-H son estimadas, "
                      "no horas reales ejecutadas.",L,143,105,8.5,GRAY,14,4)
    if not m["complete"]:
        pdf.text(L,78,"INFORME PARCIAL / EXISTEN PROGRAMACIONES SIN CERRAR",9,AMBER,True)

    # 03. Balance y especialidades (indicadores únicos).
    pdf.new_page()
    pdf.heading("02","Balance mensual de OT",
                "Los indicadores generales y programados usan órdenes de trabajo distintas.")
    pdf.donut(159,554,65,[("FINALIZADAS",m["done"],BLUE),
                          ("NO FINALIZADAS",max(0,m["total"]-m["done"]),SKY)])
    pdf.donut(436,554,65,[("PROGRAMADAS CERRADAS",m["plan_done"],TEAL),
                          ("PROGRAMADAS PEND.",max(0,m["plan"]-m["plan_done"]),SKY)])
    pdf.text(102,464,f"{_num(m['done'])} DE {_num(m['total'])} OT",11,NAVY,True)
    pdf.text(364,464,f"{_num(m['plan_done'])} DE {_num(m['plan'])} OT",11,NAVY,True)
    pdf.text(L,420,"COMPARATIVO POR ESPECIALIDAD",11,NAVY,True)
    records=[]
    for s in m["specs"]:
        records.append([
            NAMES.get(s.get("especialidad"),s.get("name") or ""),
            _num(s.get("total_ot")),_num(s.get("completed_ot")),
            _p(s.get("progress_ot_pct")),
            f"{_num(s.get('scheduled_completed'))}/{_num(s.get('scheduled_unique'))}",
            _p(s.get("scheduled_progress_ot_pct")) if _n(s.get("scheduled_unique")) else "—"])
    if records:
        pdf.simple_table(["ESPECIALIDAD","CARTERA","FINAL.","GENERAL","PROGR. OT","PROGR. %"],
                         records,[102,65,62,68,115,109],399,39,8,4)
    pdf.text(L,174,"INTERPRETACION",10,NAVY,True)
    pdf.write_wrapped("El indicador general incluye las OT finalizadas fuera de "
                      "programación. El programado usa exclusivamente OT diferentes "
                      "que fueron programadas. No se suman repeticiones semanales.",
                      L,151,102,8.8,GRAY,15,4)

    # 04. Evolución semanal.
    pdf.new_page()
    pdf.heading("03","Evolución semanal",
                "Asignaciones por semana: una misma OT puede aparecer en más de un corte.")
    weeks=_week_groups(data)
    pdf.text(L,644,"ASIGNADAS Y FINALIZADAS POR CORTE",11,NAVY,True)
    max_assigned=max((v["assigned"] for _,v in weeks),default=1)
    for i,((a,b),row) in enumerate(weeks[:6]):
        y=611-i*61
        pdf.text(L,y,a[5:]+" AL "+b[5:],9,NAVY,True)
        pdf.text(446,y,f"{_num(row['done'])} / {_num(row['assigned'])}",9,NAVY,True)
        pdf.rect(L,y-25,425,12,PALE)
        pdf.rect(L,y-25,425*row["assigned"]/max_assigned,12,SKY)
        pdf.rect(L,y-25,425*row["done"]/max_assigned,12,TEAL)
    pdf.text(L,230,"CUADRO DE SEGUIMIENTO SEMANAL",11,NAVY,True)
    rows=[[a[5:]+"-"+b[5:],_num(v["assigned"]),_num(v["done"]),
           _p(_percent(v["done"],v["assigned"])),
           "CERRADA" if v["closed"] else "ABIERTA"] for (a,b),v in weeks[:6]]
    pdf.simple_table(["CORTE","ASIGNAC.","FINALIZ.","% CORTE","ESTADO"],
                     rows,[160,96,95,85,85],213,22,8,6)
    pdf.write_wrapped("Las asignaciones no equivalen a las OT únicas de la cartera "
                      "del mes; no se usan para calcular el porcentaje general.",
                      L,98,104,8.5,GRAY,13,3)

    # 05. Especialidades.
    pdf.new_page()
    pdf.heading("04","Desempeño por especialidad",
                "Cumplimiento de la cartera, OT programadas y H-H estimadas.")
    specs=m["specs"][:4]
    for i,s in enumerate(specs):
        xx=L+(i%2)*269
        yy=431-(i//2)*228
        pdf.rect(xx,yy,258,205,WHITE,LINE)
        pdf.text(xx+12,yy+179,
                 NAMES.get(s.get("especialidad"),s.get("name") or "").upper(),
                 13,NAVY,True)
        pdf.text(xx+12,yy+142,_p(s.get("progress_ot_pct")),25,BLUE,True)
        pdf.text(xx+12,yy+123,
                 f"{_num(s.get('completed_ot'))} DE {_num(s.get('total_ot'))} OT CARTERA",8.5,INK)
        pdf.text(xx+12,yy+94,"OT PROGRAMADAS UNICAS",8,NAVY,True)
        if _n(s.get("scheduled_unique")):
            percent=_percent(s.get("scheduled_completed"),s.get("scheduled_unique"))
            pdf.rect(xx+12,yy+72,233,11,PALE)
            pdf.rect(xx+12,yy+72,233*min(100,percent)/100,11,TEAL)
            pdf.text(xx+12,yy+54,
                     f"{_num(s.get('scheduled_completed'))} / {_num(s.get('scheduled_unique'))} OT  ({_p(percent)})",
                     8.8,INK,True)
        else:
            pdf.text(xx+12,yy+62,"SIN PROGRAMACION",9,GRAY,True)
        pdf.text(xx+12,yy+21,
                 f"H-H EST.: {_num(s.get('completed_hh'),1)} DE {_num(s.get('total_hh'),1)}",
                 8,GRAY,True)
    pdf.text(L,169,"NOTA DE LECTURA",10,NAVY,True)
    pdf.write_wrapped("Los valores de H-H provienen de estimaciones de órdenes "
                      "y no son una certificación de tiempo real trabajado.",
                      L,145,102,8.8,GRAY,14,4)

    # 06. Pendientes.
    pdf.new_page()
    pdf.heading("05","Backlog y desviaciones",
                "Estado de pendientes y excepciones conocidas al cierre del mes.")
    mo=m["month"]
    cards=[
        ("Pendientes último cierre",_num(mo.get("pending")),"Estados pendientes",AMBER),
        ("No encontradas",_num(mo.get("not_found")),"Sin coincidencia",BLUE),
        ("PMP sin programar",_num(mo.get("not_programmed")),"No equivale a backlog",NAVY),
        ("Backlog heredado",_num(mo.get("from_prior_backlog")),"De períodos previos",TEAL),
    ]
    for i,(name,val,note,color) in enumerate(cards):
        x=L+(i%2)*267
        y=532-(i//2)*110
        pdf.block(x,y,255,95,name,val,note,color)
    pdf.text(L,382,"OT PENDIENTES: MUESTRA DE SEGUIMIENTO",10,NAVY,True)
    rows=[]
    for v in (data.get("unresolved") or [])[:8]:
        rows.append([
            _short(v.get("numero_ot") or "SIN OT",17),
            NAMES.get(v.get("especialidad"),v.get("especialidad") or "-"),
            _short(v.get("activo") or v.get("activo_codigo") or "-",27),
            _short(v.get("resultado") or "PENDIENTE",12),
        ])
    if rows:
        pdf.simple_table(["OT","ESPECIALIDAD","EQUIPO","RESULTADO"],
                         rows,[107,124,179,111],361,27,8,8)
    else:
        pdf.rect(L,290,PAGE_WIDTH,70,PALE,LINE)
        pdf.write_wrapped("Sin OT pendientes detalladas en la consulta del cierre.",
                          L+12,330,98,9,GRAY,15,2)
    pdf.write_wrapped("Los pendientes, el PMP sin programar y el backlog heredado "
                      "son categorías distintas; no deben sumarse como si "
                      "fueran el mismo saldo.",L,92,101,8.1,GRAY,12,3)

    # 07. Conclusiones.
    pdf.new_page()
    pdf.heading("06","Conclusiones gerenciales",
                "Lectura ejecutiva, acciones sugeridas y trazabilidad.")
    pdf.text(L,649,"MENSAJES PRINCIPALES",11,NAVY,True)
    findings=[
        f"La cartera suma {_num(m['total'])} órdenes distintas; "
        f"{_num(m['done'])} están finalizadas ({_p(m['general_pct'])}).",
        f"Las OT programadas cerradas fueron {_num(m['plan_done'])} de "
        f"{_num(m['plan'])} diferentes ({_p(m['planned_pct'])}).",
        f"Se identificaron {_num(m['unplanned'])} OT finalizadas fuera "
        "de programación registradas.",
        f"Se excluyeron {_num(m['extras'])} asignaciones adicionales por "
        "reprogramación al calcular OT únicas.",
    ]
    y=622
    for i, finding in enumerate(findings,1):
        pdf.text(L,y,f"{i:02d}",11,TEAL,True)
        y=pdf.write_wrapped(finding,L+34,y,91,9.8,INK,15,3)-15
    pdf.text(L,438,"PLAN DE ACCION RECOMENDADO",11,NAVY,True)
    pdf.simple_table(["ETAPA","ACCION","RESP. SUGERIDO"],
                     [
                         ["01","Conciliar pendientes","Mantenimiento"],
                         ["02","Revisar OT fuera de plan","Planeación"],
                         ["03","Analizar reprogramación","Planeación"],
                     ],[52,299,170],416,39,8.5,3)
    pdf.text(L,230,"ALCANCE Y TRAZABILIDAD",10,NAVY,True)
    pdf.write_wrapped("Fuente: plataforma PROGRAMACION TEAM FOOD, cartera mensual "
                      "PMP, backlog y cierres semanales. OT distintas por mes; "
                      "H-H calculadas como estimaciones. Las recomendaciones "
                      "no implican aprobación ni cierre formal automático.",
                      L,207,97,9,GRAY,15,6)
    pdf.text(L,87,"ELABORADO POR C.E.K GLOBAL INSPECTION SERVICES S.A.S.",
             9,NAVY,True)
    filename=f"informe_gerencial_cierre_mensual_{year}_{month:02d}.pdf"
    return pdf.finish(),filename
