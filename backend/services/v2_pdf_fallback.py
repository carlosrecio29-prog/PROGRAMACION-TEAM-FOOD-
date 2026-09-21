"""Visual, self-contained PDF reports: vector charts and tables, no external PDF package.

Only reads the progress/closure snapshots supplied by the caller. Designed to run
on Vercel even when ReportLab is not available.
"""
from __future__ import annotations

from datetime import date
from math import cos, pi, sin
from typing import Any

NAVY = (.075, .153, .278)
BLUE = (.145, .420, .700)
SKY = (.855, .922, .969)
GREEN = (.090, .530, .423)
MINT = (.868, .953, .929)
AMBER = (.800, .490, .125)
CREAM = (.989, .948, .871)
RED = (.760, .295, .315)
PINK = (.987, .919, .918)
PALE = (.952, .969, .988)
GRAY = (.435, .506, .580)
LINE = (.841, .878, .914)
WHITE = (1, 1, 1)
INK = (.160, .231, .329)
NAMES = {"MEC": "MECÁNICA", "ELE": "ELÉCTRICA",
         "MET": "METROLOGÍA", "SER": "SERVICIOS"}
MONTHS = ("","ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
          "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE")


def _esc(value: Any) -> bytes:
    return str(value if value is not None else "").replace("\\", "\\\\").replace(
        "(", "\\(").replace(")", "\\)").encode("cp1252", "replace")


def _fmt(value, decimals=0):
    return f"{float(value or 0):,.{decimals}f}".replace(",", "¬").replace(
        ".", ",").replace("¬", ".")


def _pct(done, total):
    return 100 * float(done or 0) / float(total or 1) if total else 0.


def _clip(value, max_chars=28):
    text = str(value if value is not None else "—").replace("\n", " ").strip()
    return text if len(text) <= max_chars else text[:max_chars - 1].rstrip() + "…"


class _PDF:
    W, H = 842, 595

    def __init__(self, title, subtitle, tag):
        self.pages = []
        self.parts = []
        self.y = 0
        self.title = title
        self.subtitle = subtitle
        self.tag = tag
        self.page_number = 0
        self.new_page()

    def emit(self, command):
        self.parts.append(command.encode("ascii") if isinstance(command, str) else command)

    @staticmethod
    def rgb(color):
        return "%.3f %.3f %.3f" % color

    def rect(self, x, y, w, h, fill=PALE, stroke=None):
        self.emit(self.rgb(fill) + " rg")
        if stroke:
            self.emit(self.rgb(stroke) + " RG %.2f w" % .65)
        self.emit("%.2f %.2f %.2f %.2f re %s" %
                  (x, y, max(0, w), max(0, h), "B" if stroke else "f"))

    def text(self, x, y, value, size=9, color=INK, bold=False):
        font = "F2" if bold else "F1"
        self.emit(self.rgb(color) + " rg")
        self.emit(b"BT /" + font.encode() + (" %.2f Tf " % size).encode()
                  + ("1 0 0 1 %.2f %.2f Tm " % (x, y)).encode()
                  + b"(" + _esc(value) + b") Tj ET")

    def rule(self, x1, y1, x2, y2, color=LINE, width=.7):
        self.emit(self.rgb(color) + " RG %.2f w" % width)
        self.emit("%.2f %.2f m %.2f %.2f l S" % (x1,y1,x2,y2))

    def new_page(self):
        if self.parts:
            self.pages.append(b"\n".join(self.parts))
        self.parts = []
        self.page_number += 1
        self.rect(0, 0, self.W, self.H, WHITE)
        self.rect(0, 531, self.W, 64, NAVY)
        self.rect(0, 531, 8, 64, BLUE)
        self.text(31, 573, "TEAM FOODS   /   C.E.K GLOBAL INSPECTION", 10, WHITE, True)
        self.text(31, 547, self.title, 17, WHITE, True)
        self.text(810 - len(self.tag)*5.3, 551, self.tag, 9, SKY, True)
        self.rect(0, 0, self.W, 37, PALE)
        self.text(31, 15, self.subtitle, 8, GRAY)
        self.text(768, 15, "PÁGINA %02d" % self.page_number, 8, NAVY, True)
        self.y = 510

    def ensure(self, height):
        if self.y - height < 53:
            self.new_page()

    def section(self, title, subtitle=None):
        self.ensure(39)
        self.text(31, self.y, title.upper(), 11, NAVY, True)
        self.rule(31, self.y-7, 810, self.y-7, LINE)
        self.y -= 21
        if subtitle:
            self.text(31, self.y, _clip(subtitle, 118), 8, GRAY)
            self.y -= 18

    def badge(self, label, fill=SKY, fg=NAVY):
        width = 14 + len(label)*5.5
        self.rect(31, self.y-4, width, 19, fill)
        self.text(38, self.y+2, label, 8.3, fg, True)
        self.y -= 26

    def card(self, x, y, width, height, label, value, note="", color=BLUE,
             tint=PALE):
        self.rect(x,y,width,height,WHITE,LINE)
        self.rect(x,y,width,5,color)
        self.text(x+12,y+height-19,_clip(label.upper(),32),8,GRAY,True)
        self.text(x+12,y+height-51,_clip(value,22),23,color,True)
        self.text(x+12,y+12,_clip(note,40),7,GRAY)

    def cards(self, metrics, cols=4):
        width = (779-(cols-1)*11)/cols
        rows = (len(metrics)+cols-1)//cols
        needed = rows*88 + (rows-1)*11
        self.ensure(needed)
        for i, metric in enumerate(metrics):
            col = i%cols
            row = i//cols
            x=31+col*(width+11)
            y=self.y-row*99-88
            self.card(x,y,width,88,*metric)
        self.y-=needed+14

    def progress(self, x, y, width, label, done, total, color=BLUE, note=""):
        self.text(x,y+22,label,9,NAVY,True)
        self.text(x+width-52,y+22,"%s%%" % _fmt(_pct(done,total),1),10,color,True)
        self.rect(x,y,width,12,PALE)
        self.rect(x,y,width*min(1.,_pct(done,total)/100),12,color)
        if note:
            self.text(x,y-13,_clip(note,70),7.5,GRAY)

    def paragraph(self, value, maxchars=113, size=9, gap=13):
        text = str(value)
        while text:
            if len(text)<=maxchars:
                line,text=text,""
            else:
                split=text.rfind(" ",0,maxchars)
                if split<20: split=maxchars
                line,text=text[:split],text[split:].lstrip()
            self.ensure(gap+4)
            self.text(31,self.y,line,size,INK)
            self.y-=gap

    def bar_chart(self, rows, value_key="programmed", done_key="finalized",
                  *, label_key="label", width=760, max_rows=8):
        shown=rows[:max_rows]
        need=24+len(shown)*31
        self.ensure(need)
        maxval=max([float(r.get(value_key) or 0) for r in shown]+[1])
        for row in shown:
            label=_clip(row.get(label_key) or "—",29)
            left=183
            w=480
            self.text(31,self.y+1,label,8,INK,True)
            self.rect(left,self.y-1,w,11,PALE)
            total=float(row.get(value_key) or 0)
            done=float(row.get(done_key) or 0)
            self.rect(left,self.y-1,w*total/maxval,11,SKY)
            self.rect(left,self.y-1,w*max(0,done)/maxval,11,GREEN)
            self.text(left+w+12,self.y,("%s / %s" % (_fmt(done),_fmt(total))),8,NAVY,True)
            self.y-=31
        self.y-=8

    def donut(self, x, y, r, segments):
        total=sum(max(0,float(v)) for _,v,_ in segments)
        if total<=0:
            self.circle(x,y,r,SKY)
        else:
            angle=pi/2
            for _,amount,color in segments:
                portion=max(0,float(amount))/total
                if portion<=0:continue
                end=angle+portion*2*pi
                self.slice(x,y,r,angle,end,color)
                angle=end
        self.circle(x,y,r*.62,WHITE)
        self.text(x-16,y+2,"%s%%" % _fmt(_pct(segments[0][1],total),0),12,GREEN,True)
        self.text(x-20,y-12,"CERRADAS",6.5,GRAY,True)

    def circle(self,x,y,r,color):
        k=.55228475
        self.emit(self.rgb(color)+" rg")
        self.emit("%.2f %.2f m" %(x+r,y))
        for vals in (
            (x+r,y+k*r,x+k*r,y+r,x,y+r),
            (x-k*r,y+r,x-r,y+k*r,x-r,y),
            (x-r,y-k*r,x-k*r,y-r,x,y-r),
            (x+k*r,y-r,x+r,y-k*r,x+r,y)):
            self.emit(" ".join("%.2f"%n for n in vals)+" c")
        self.emit("h f")

    def slice(self,x,y,r,start,end,color):
        self.emit(self.rgb(color)+" rg")
        self.emit("%.2f %.2f m %.2f %.2f l" %
                  (x,y,x+r*cos(start),y+r*sin(start)))
        angle=start
        while angle<end-1e-8:
            nxt=min(angle+pi/2,end)
            k=4./3.*__import__("math").tan((nxt-angle)/4.)
            a=(x+r*cos(angle),y+r*sin(angle))
            b=(x+r*cos(nxt),y+r*sin(nxt))
            controls=(a[0]-r*k*sin(angle),a[1]+r*k*cos(angle),
                      b[0]+r*k*sin(nxt),b[1]-r*k*cos(nxt),b[0],b[1])
            self.emit(" ".join("%.2f"%n for n in controls)+" c")
            angle=nxt
        self.emit("h f")

    def table(self, columns, rows, widths, row_height=22, repeat_title=None):
        assert len(columns)==len(widths)
        assert sum(widths)<=780
        def header():
            self.ensure(29+row_height)
            x=31
            self.rect(31,self.y-25,779,28,NAVY)
            for title,w in zip(columns,widths):
                self.text(x+6,self.y-16,_clip(title,int((w-12)/4.3)),7.2,WHITE,True)
                x+=w
            self.y-=28
        header()
        for index,row in enumerate(rows):
            if self.y-row_height < 52:
                self.new_page()
                if repeat_title:
                    self.section(repeat_title)
                header()
            if index%2==0:self.rect(31,self.y-row_height,779,row_height,PALE)
            x=31
            for value,w in zip(row,widths):
                cap=max(3,int((w-12)/4.3))
                self.text(x+6,self.y-row_height+7,_clip(value,cap),7.2,INK)
                x+=w
            self.rule(31,self.y-row_height,810,self.y-row_height,LINE,.3)
            self.y-=row_height
        self.y-=12

    def finish(self):
        self.pages.append(b"\n".join(self.parts))
        objects=[]
        def add(value):
            objects.append(value)
            return len(objects)
        normal=add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        bold=add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        pages=add(b"")
        refs=[]
        for stream in self.pages:
            content=add(b"<< /Length %d >>\nstream\n"%len(stream)+stream+b"\nendstream")
            refs.append(add(
                b"<< /Type /Page /Parent "+str(pages).encode()+b" 0 R "
                b"/MediaBox [0 0 842 595] /Resources << /Font << /F1 "
                +str(normal).encode()+b" 0 R /F2 "+str(bold).encode()+b" 0 R >> >> "
                +b"/Contents "+str(content).encode()+b" 0 R >>"
            ))
        objects[pages-1]=b"<< /Type /Pages /Count %d /Kids [%s] >>"%(
            len(refs),b" ".join(f"{ref} 0 R".encode() for ref in refs))
        root=add(b"<< /Type /Catalog /Pages "+str(pages).encode()+b" 0 R >>")
        output=bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets=[0]
        for i,obj in enumerate(objects,1):
            offsets.append(len(output))
            output.extend(f"{i} 0 obj\n".encode()+obj+b"\nendobj\n")
        position=len(output)
        output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
        for offset in offsets[1:]:output.extend(f"{offset:010d} 00000 n \n".encode())
        output.extend(b"trailer\n<< /Size "+str(len(objects)+1).encode()
                      +b" /Root "+str(root).encode()+b" 0 R >>\nstartxref\n"
                      +str(position).encode()+b"\n%%EOF\n")
        return bytes(output)


def _name(week):
    return "%s–%s · %s" % (week["week_from"][5:],week["week_to"][5:],
                             week["especialidad"])


def _summary(pdf, label, summary, monthly=False):
    pdf.section("Indicadores principales", "Cada tarjeta refleja datos verificados en los cierres.")
    metrics=[
        ("OT distintas" if monthly else "OT programadas",_fmt(summary["programmed"]),
         "Sin duplicar reprogramadas" if monthly else "Actividades de la semana",BLUE,PALE),
        ("Finalizadas",_fmt(summary["finalized"]),"Resultado del cierre",GREEN,MINT),
        ("Pendientes",_fmt(summary["pending"]),"Por atender",AMBER,CREAM),
        ("No encontradas",_fmt(summary["not_found"]),"Requieren conciliación",RED,PINK),
        ("HH programadas",_fmt(summary["hh_programmed"],1),
         "Suma de semanas; estimadas",BLUE,PALE),
        ("HH de OT cerradas",_fmt(summary["hh_finalized"],1),
         "Estimadas; no horas reales",GREEN,MINT),
        ("Cumplimiento OT",_fmt(_pct(summary["finalized"],summary["programmed"]),1)+"%",
         "Sobre OT programadas",BLUE,PALE),
        ("Cumplimiento HH",_fmt(_pct(summary["hh_finalized"],summary["hh_programmed"]),1)+"%",
         "Sobre HH estimadas",GREEN,MINT),
    ]
    pdf.cards(metrics)


def _kpi_note(pdf, summary, monthly=False):
    pdf.section("Lectura del cierre")
    period = "En el mes" if monthly else "En esta semana"
    pdf.paragraph(
        f"{period} se programaron {_fmt(summary['programmed'])} "
        f"{'OT distintas' if monthly else 'actividades'}. "
        f"Finalizaron {_fmt(summary['finalized'])}, quedaron "
        f"{_fmt(summary['pending'])} pendientes y "
        f"{_fmt(summary['not_found'])} no encontradas. "
        f"El cumplimiento fue {_fmt(_pct(summary['finalized'], summary['programmed']),1)}% "
        f"por OT y {_fmt(_pct(summary['hh_finalized'],summary['hh_programmed']),1)}% "
        f"por HH estimadas."
    )
    pdf.y-=8


def _status_and_progress(pdf, summary):
    pdf.section("Distribución del resultado y cumplimiento")
    pdf.ensure(151)
    center_y=pdf.y-70
    segments=[
        ("FINALIZADAS",summary["finalized"],GREEN),
        ("PENDIENTES",summary["pending"],AMBER),
        ("NO ENCONTRADAS",summary["not_found"],RED),
        ("SIN VERIFICAR",summary.get("unchecked",0),GRAY),
    ]
    pdf.donut(118,center_y,54,segments)
    legend_y=pdf.y-20
    for label,count,color in segments:
        pdf.rect(199,legend_y-3,9,9,color)
        pdf.text(215,legend_y,label+"   "+_fmt(count),8,INK)
        legend_y-=25
    pdf.progress(435,pdf.y-35,343,"CUMPLIMIENTO POR OT",
                 summary["finalized"],summary["programmed"],GREEN)
    pdf.progress(435,pdf.y-105,343,"CUMPLIMIENTO POR HH",
                 summary["hh_finalized"],summary["hh_programmed"],BLUE,
                 "HH estimadas; no horas reales")
    pdf.y-=156


def _weekly_rows(pdf,weeks):
    pdf.section("Evolución semanal", "Barras verdes: finalizadas | barras azules: programadas.")
    chart=[{**w,"label":_name(w)} for w in weeks]
    pdf.bar_chart(chart,max_rows=len(chart))
    pdf.section("Cuadro comparativo", "La misma OT puede figurar en varias semanas si pasó por backlog.")
    rows=[]
    for w in weeks:
        rows.append([
            w["week_from"][5:]+"-"+w["week_to"][5:],w["especialidad"],w["estado"][:5],
            _fmt(w["programmed"]),_fmt(w["finalized"]),_fmt(w["pending"]),
            _fmt(w["not_found"]),_fmt(w["hh_programmed"],1),
            _fmt(w["hh_finalized"],1),
            _fmt(_pct(w["finalized"],w["programmed"]),1)+"%",
        ])
    pdf.table(["CORTE","ESP.","CIERRE","PROG.","FINAL.","PEND.","NO ENC.",
               "HH PROG.","HH FIN.","OT %"],rows,
              [103,46,58,62,59,57,62,97,99,76],repeat_title="Comparativo semanal")


def _specialty_rows(pdf, data):
    if not data.get("specialties"):
        return
    pdf.section("Comparativo por especialidad",
                "Eventos semanales; no equivale a OT únicas de todo el mes.")
    rows=[]
    for s in data["specialties"]:
        rows.append([NAMES.get(s["especialidad"],s["especialidad"]),
                     _fmt(s["programmed"]),_fmt(s["finalized"]),_fmt(s["pending"]),
                     _fmt(s["not_found"]),_fmt(s["hh_programmed"],1),
                     _fmt(s["hh_finalized"],1),
                     _fmt(_pct(s["finalized"],s["programmed"]),1)+"%"])
    pdf.table(["ESPECIALIDAD","PROG.","FINAL.","PEND.","NO ENC.",
               "HH PROG.","HH FIN.","OT %"],rows,
              [161,78,77,75,81,111,112,84])


def _detail_table(pdf, rows, monthly=False):
    if not rows:
        return
    pdf.new_page()
    pdf.section("Detalle de OT no finalizadas" if monthly else "Detalle técnico de órdenes",
                "Estado del último cierre (sin duplicados)" if monthly
                else "Resultado y condición de cada actividad programada.")
    cols=["OT","ESPECIALIDAD","EQUIPO","PLAN DE TRABAJO",
          "ESTADO","HH EST."]
    table_rows=[]
    for item in rows:
        table_rows.append([
            item.get("numero_ot") or "SIN ASIGNAR",
            item.get("especialidad") or "",
            item.get("activo") or item.get("activo_codigo") or "",
            item.get("plan") or item.get("plan_trabajo") or "",
            item.get("resultado") or item.get("estado_cierre") or "SIN VERIFICAR",
            _fmt(item.get("hh_estimada",item.get("hh_programadas",0)),2),
        ])
    pdf.table(cols,table_rows,[128,92,136,255,103,65],
              row_height=22,repeat_title="Detalle de OT (continuación)")


def render_progress_fallback(data: dict[str,Any],year:int,month:int,
                             programming_id:int|None=None,
                             detail_rows:list[dict[str,Any]]|None=None)->tuple[bytes,str]:
    weeks=data["weeks"]
    if programming_id is not None:
        weeks=[w for w in weeks if w["programming_id"]==programming_id]
        if not weeks:raise ValueError("La programación no corresponde al mes indicado")
    if not weeks:raise ValueError("No hay programaciones para generar el reporte")
    monthly=programming_id is None
    summary=data["monthly"] if monthly else weeks[0]
    weekly_totals=data["weekly_totals"]
    # Month uses unique OT outcomes, but HH sum every scheduled weekly activity.
    if monthly:
        summary={**summary,"hh_programmed":weekly_totals["hh_programmed"],
                 "hh_finalized":weekly_totals["hh_finalized"]}
    name=("INFORME GENERAL DE CIERRE MENSUAL" if monthly
          else "INFORME DE CIERRE SEMANAL")
    subtitle=(f"{MONTHS[month]} {year}  |  PLANTA BARRANQUILLA" if monthly else
              f"{weeks[0]['week_from']} AL {weeks[0]['week_to']}  |  "
              f"{NAMES.get(weeks[0]['especialidad'], weeks[0]['especialidad'])}")
    pdf=_PDF(name,subtitle,("MENSUAL" if monthly else "SEMANAL"))
    pdf.text(31,502,"REPORTE DE MANTENIMIENTO / C.E.K",8,GRAY,True)
    pdf.y=476
    anticipated=any(w["estado"]=="CERRADA" and w["semana_fin"]>date.today()
                    for w in weeks)
    if anticipated:pdf.badge("CIERRE ANTICIPADO / PRUEBA",CREAM,AMBER)
    if monthly:
        pdf.badge(f"{summary['weeks_closed']} DE {summary['weeks_total']} PROGRAMACIONES CERRADAS",
                  MINT if summary["all_weeks_closed"] else CREAM,
                  GREEN if summary["all_weeks_closed"] else AMBER)
    elif weeks[0]["estado"]!="CERRADA":
        pdf.badge("SIN CIERRE CONFIRMADO / INFORME PARCIAL",CREAM,AMBER)
    _summary(pdf,"INDICADORES",summary,monthly)
    _status_and_progress(pdf,summary)
    _kpi_note(pdf,summary,monthly)
    if pdf.y < 205:
        pdf.new_page()
    if monthly:
        pdf.section("Alcance del mes")
        pdf.cards([
            ("Registros PMP",_fmt(summary["pmp_count"]),"Mantenimiento; OPERACIÓN excluida",BLUE,PALE),
            ("OT únicas",_fmt(summary["programmed"]),"Reprogramaciones sin duplicar",GREEN,MINT),
            ("PMP sin programar",_fmt(summary["not_programmed"]),"No equivale a backlog",AMBER,CREAM),
            ("Backlog heredado",_fmt(summary["from_prior_backlog"]),"OT de periodos anteriores",BLUE,PALE),
        ])
        pdf.paragraph("El resumen de OT finalizadas se calcula sobre órdenes distintas según "
                      "su último cierre. Las HH representan estimaciones por actividad semanal; "
                      "una OT reprogramada puede aportar HH en más de una semana.",maxchars=118)
        pdf.y-=10
        _weekly_rows(pdf,weeks)
        pdf.new_page()
        _specialty_rows(pdf,data)
        pdf.section("Balance y criterios")
        pdf.paragraph(
            f"Se registraron {_fmt(summary['programmed'])} OT únicas: "
            f"{_fmt(summary['finalized'])} finalizadas, {_fmt(summary['pending'])} pendientes, "
            f"{_fmt(summary['not_found'])} no encontradas y "
            f"{_fmt(summary.get('unchecked',0))} sin verificar. "
            "El cumplimiento por HH usa estimaciones del plan y no sustituye las horas reales.",
            maxchars=115)
        if not summary["all_weeks_closed"]:
            pdf.badge("INFORME PARCIAL: EXISTEN PROGRAMACIONES SIN CERRAR",CREAM,AMBER)
        _detail_table(pdf,data.get("unresolved",[]),monthly=True)
    else:
        pdf.section("OT programadas y finalizadas")
        pdf.bar_chart([{**weeks[0],"label":NAMES.get(weeks[0]["especialidad"],
                      weeks[0]["especialidad"])}])
        pdf.section("Resultados del cierre semanal")
        w=weeks[0]
        pdf.table(["PROGRAMADAS","FINALIZADAS","PENDIENTES","NO ENCONTRADAS",
                   "HH EST. PROG.","HH EST. CERRADAS"],
                  [[_fmt(w["programmed"]),_fmt(w["finalized"]),_fmt(w["pending"]),
                    _fmt(w["not_found"]),_fmt(w["hh_programmed"],2),
                    _fmt(w["hh_finalized"],2)]],
                  [129,129,129,129,131,132])
        pdf.section("Criterios del informe")
        pdf.paragraph("La clasificación del cierre se toma del calendario de mantenimiento "
                      "conciliado con las OT programadas. Las HH son estimaciones de las "
                      "actividades, no tiempos de ejecución reportados por técnicos.",
                      maxchars=118)
        _detail_table(pdf,detail_rows or [],monthly=False)
    kind="mensual" if monthly else "semanal"
    filename=(f"informe_{kind}_mtto_{year}_{month:02d}"
              +(f"_{programming_id}" if programming_id is not None else "")+".pdf")
    return pdf.finish(),filename
