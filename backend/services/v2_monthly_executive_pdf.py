"""Informe mensual gerencial A4, generado bajo demanda con datos de cierre V2.

Las magnitudes son de solo lectura. No genera hallazgos de equipo o causas
que no estén sustentadas por el seguimiento y los cierres en la aplicación.
El informe semanal conserva su generador y estilo anteriores.
"""
from __future__ import annotations

from base64 import b64decode
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from math import pi, sin, cos
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

NAVY = colors.HexColor("#103750")
DARK = colors.HexColor("#092E46")
BLUE = colors.HexColor("#1387B6")
TEAL = colors.HexColor("#148998")
LIGHT = colors.HexColor("#EAF2F6")
PALE = colors.HexColor("#F4F8FA")
INK = colors.HexColor("#29465D")
MUTED = colors.HexColor("#60798D")
BORDER = colors.HexColor("#D7E4EB")
WHITE = colors.white
AMBER = colors.HexColor("#CE9243")
MINT = colors.HexColor("#E7F4F0")
NAMES = {"MEC": "Mecánica", "ELE": "Eléctrica",
         "MET": "Metrología", "SER": "Servicios"}
MONTHS = ("", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
          "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE")
W, H = A4
LEFT = 42
RIGHT = W - LEFT
CONTENT_W = RIGHT - LEFT
PAGES = 7


def _n(value: Any) -> float:
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.


def _num(value: Any, digits: int = 0) -> str:
    result = f"{_n(value):,.{digits}f}"
    return result.replace(",", "\u00a7").replace(".", ",").replace("\u00a7", ".")


def _percent(done: Any, total: Any) -> float:
    total = _n(total)
    return round(100 * _n(done) / total, 1) if total else 0.


def _pct(value: Any) -> str:
    return _num(value, 1) + "%"


def _load_logo(name: str):
    try:
        raw = (Path(__file__).resolve().parents[1] / "assets" / name).read_text()
        return ImageReader(BytesIO(b64decode(raw)))
    except (OSError, ValueError):
        return None


def _text(c, x: float, y: float, text: Any, size=10, color=INK,
          bold=False, align="left"):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.setFillColor(color)
    text = str(text if text is not None else "")
    if align == "center":
        c.drawCentredString(x, y, text)
    elif align == "right":
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)


def _lines(content: Any, max_width: float, size=10, bold=False):
    font = "Helvetica-Bold" if bold else "Helvetica"
    words = str(content or "").replace("\n", " \n ").split()
    lines, line = [], ""
    for word in words:
        if word == "\n":
            if line:
                lines.append(line)
            line = ""
            continue
        candidate = f"{line} {word}".strip()
        if pdfmetrics.stringWidth(candidate, font, size) <= max_width:
            line = candidate
            continue
        if line:
            lines.append(line)
            line = ""
        # Los códigos largos o nombres sin espacios no deben desbordarse.
        if pdfmetrics.stringWidth(word, font, size) > max_width:
            chunk = ""
            for char in word:
                if chunk and pdfmetrics.stringWidth(chunk + char, font, size) > max_width:
                    lines.append(chunk)
                    chunk = char
                else:
                    chunk += char
            line = chunk
        else:
            line = word
    if line:
        lines.append(line)
    return lines


def _para(c, x, y, content, width, size=10, leading=15, color=INK,
          bold=False, max_lines=None):
    lines = _lines(content, width, size, bold)
    if max_lines is not None:
        lines = lines[:max_lines]
    for line in lines:
        _text(c, x, y, line, size, color, bold)
        y -= leading
    return y


def _rounded(c, x, y, w, h, fill=WHITE, border=BORDER, radius=11):
    c.setLineWidth(.8)
    c.setStrokeColor(border)
    c.setFillColor(fill)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def _logo(c, img, x, y, w, h):
    if img is not None:
        c.drawImage(img, x, y, width=w, height=h, preserveAspectRatio=True,
                    anchor="c", mask="auto")


def _industry_line_art(c, y0: float, color=BLUE):
    """Planta industrial estilizada: silueta vectorial, no un activo real."""
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(1.1)
    for x, tower_h in ((55, 126), (110, 158), (168, 108), (322, 169), (388, 117)):
        c.rect(x, y0, 30, tower_h, fill=0, stroke=1)
        c.line(x + 15, y0 + tower_h, x + 15, y0 + tower_h + 15)
        for y in range(int(y0 + 22), int(y0 + tower_h), 21):
            c.line(x + 3, y, x + 27, y)
    c.rect(221, y0, 80, 79, fill=0, stroke=1)
    c.line(221, y0 + 52, 301, y0 + 52)
    c.line(238, y0 + 79, 238, y0 + 111)
    c.line(238, y0 + 111, 317, y0 + 111)
    c.line(317, y0 + 111, 317, y0 + 169)
    c.rect(445, y0, 66, 75, fill=0, stroke=1)
    c.circle(478, y0 + 36, 22, stroke=1, fill=0)
    c.line(37, y0 + 21, 545, y0 + 21)
    c.line(65, y0 + 45, 245, y0 + 45)
    c.line(301, y0 + 43, 456, y0 + 43)
    c.restoreState()


def _cover(c, year, month, issue_date, code, cek_logo, team_logo, complete):
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    p = c.beginPath()
    p.moveTo(0, H)
    p.lineTo(360, H)
    p.lineTo(242, H - 122)
    p.lineTo(0, H - 122)
    p.close()
    c.setFillColor(NAVY)
    c.drawPath(p, fill=1, stroke=0)
    p = c.beginPath()
    p.moveTo(0, H - 132)
    p.lineTo(0, H - 186)
    p.lineTo(105, H - 81)
    p.lineTo(160, H - 81)
    p.close()
    c.setFillColor(BLUE)
    c.drawPath(p, fill=1, stroke=0)

    c.setStrokeColor(LIGHT)
    c.setLineWidth(.6)
    for y in range(525, 815, 28):
        c.line(360, y, W, y)
    for x in range(350, 600, 28):
        c.line(x, 518, x, H)

    # Uso del logotipo C.E.K almacenado en la propia aplicación.
    _rounded(c, 148, 596, 300, 122, WHITE, LIGHT, 13)
    _logo(c, cek_logo, 186, 600, 224, 113)
    _text(c, W / 2, 568, "INFORME GERENCIAL", 29, NAVY, True, "center")
    _text(c, W / 2, 535, "DE MANTENIMIENTO", 24, INK, True, "center")
    c.setStrokeColor(TEAL)
    c.setLineWidth(3)
    c.line(114, 519, W - 114, 519)
    _text(c, W/2, 485, "Consolidado mensual de programación,", 14, NAVY, True, "center")
    _text(c, W/2, 466, "cumplimiento y backlog", 14, NAVY, True, "center")
    _text(c, W/2, 438, "Planta Barranquilla  |  Team Foods", 11, MUTED, False, "center")

    # Franja de planta vectorial y líneas técnicas, en lugar de fotografía no verificable.
    c.setFillColor(LIGHT)
    c.rect(0, 188, W, 212, fill=1, stroke=0)
    _industry_line_art(c, 190, colors.HexColor("#A4C5D7"))
    c.setFillColor(PALE)
    p = c.beginPath()
    p.moveTo(0, 190)
    p.lineTo(0, 290)
    p.lineTo(124, 190)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    p = c.beginPath()
    p.moveTo(W, 190)
    p.lineTo(W, 270)
    p.lineTo(W - 96, 190)
    p.close()
    c.setFillColor(BLUE)
    c.drawPath(p, fill=1, stroke=0)

    c.setFillColor(NAVY)
    c.rect(0, 0, W, 153, fill=1, stroke=0)
    _text(c, LEFT, 124, f"{MONTHS[month]} {year}", 19, WHITE, True)
    _text(c, LEFT, 98, "Entregable para Team Foods", 10, colors.HexColor("#C3E4F1"))
    _text(c, LEFT, 76, "C.E.K Global Inspection Services S.A.S.", 9, WHITE, True)
    _text(c, LEFT, 55, f"{code}  |  Rev. 00  |  {issue_date}", 8.5, colors.HexColor("#C3E4F1"))
    _text(c, LEFT, 29,
          "PROGRAMACIONES CERRADAS" if complete else "INFORME PARCIAL · PROGRAMACIONES ABIERTAS",
          8.2, colors.HexColor("#A5D5E8"), True)
    _logo(c, team_logo, W - 174, 58, 126, 61)
    c.showPage()


def _footer(c, page_number, code, issue_date):
    c.setStrokeColor(BORDER)
    c.setLineWidth(.7)
    c.line(LEFT, 55, RIGHT, 55)
    _text(c, LEFT, 39, "C.E.K / TEAM FOODS  ·  INFORME GERENCIAL DE MANTENIMIENTO",
          7.2, MUTED, True)
    _text(c, RIGHT, 39, f"{code}  |  Rev. 00  |  {issue_date}  |  Pág. {page_number} / {PAGES}",
          7.2, MUTED, False, "right")


def _page(c, page_number, kicker, title, subtitle, code, issue_date):
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    _text(c, RIGHT, 808, "C.E.K / TEAM FOODS   ·   INFORME GERENCIAL",
          8, NAVY, True, "right")
    c.setStrokeColor(BORDER)
    c.line(LEFT, 796, RIGHT, 796)
    _text(c, LEFT, 768, kicker.upper(), 9, TEAL, True)
    _text(c, LEFT, 731, title, 23, NAVY, True)
    _para(c, LEFT, 710, subtitle, CONTENT_W, size=9.6, leading=14,
          color=MUTED, max_lines=2)
    c.setFillColor(TEAL)
    c.rect(LEFT, 679, 94, 4, stroke=0, fill=1)
    c.setFillColor(LIGHT)
    c.rect(LEFT + 95, 679, CONTENT_W - 95, 4, stroke=0, fill=1)
    _footer(c, page_number, code, issue_date)


def _section(c, y, title):
    _text(c, LEFT, y, title.upper(), 10.2, NAVY, True)
    return y - 15


def _tile(c, x, y, width, label, value, note="", accent=BLUE, height=82):
    _rounded(c, x, y, width, height, PALE, BORDER, 9)
    c.setFillColor(accent)
    c.roundRect(x, y + height - 5, width, 5, 2, stroke=0, fill=1)
    _text(c, x + 13, y + height - 24, label.upper(), 8, MUTED, True)
    _text(c, x + 13, y + height - 55, value, 22, accent, True)
    if note:
        _para(c, x + 13, y + 16, note, width - 26, 7.6, 10, MUTED, max_lines=2)


def _progress(c, x, y, width, label, percentage, subtitle="", color=BLUE):
    _text(c, x, y + 27, label, 9, NAVY, True)
    _text(c, x + width, y + 27, _pct(percentage), 11, color, True, "right")
    c.setFillColor(LIGHT)
    c.roundRect(x, y + 7, width, 13, 6, fill=1, stroke=0)
    progress = max(0, min(100, _n(percentage))) / 100
    if progress:
        c.setFillColor(color)
        c.roundRect(x, y + 7, width * progress, 13, 6, fill=1, stroke=0)
    if subtitle:
        _text(c, x, y - 9, subtitle, 8, MUTED)


def _ring(c, x, y, radius, percentage, title, detail, color=BLUE):
    c.setLineWidth(14)
    c.setStrokeColor(LIGHT)
    c.circle(x, y, radius, stroke=1, fill=0)
    percentage = max(0, min(100, _n(percentage)))
    if percentage:
        p = c.beginPath()
        start = pi / 2
        end = start + percentage * pi / 50
        steps = max(8, int(percentage // 3) + 1)
        for i in range(steps + 1):
            ang = start + (end - start) * i / steps
            point = (x + radius * cos(ang), y + radius * sin(ang))
            if i == 0:
                p.moveTo(*point)
            else:
                p.lineTo(*point)
        c.setStrokeColor(color)
        c.setLineCap(1)
        c.drawPath(p, stroke=1, fill=0)
    _text(c, x, y + 2, _pct(percentage), 18, NAVY, True, "center")
    _text(c, x, y - 16, title, 7.4, MUTED, True, "center")
    _text(c, x, y - radius - 29, detail, 9, NAVY, True, "center")


def _table(c, x, top, widths, headers, rows, row_h=30, sizes=None):
    sizes = sizes or [8] * len(widths)
    table_w = sum(widths)
    c.setFillColor(NAVY)
    c.roundRect(x, top - 31, table_w, 31, 5, stroke=0, fill=1)
    off = x
    for h, width in zip(headers, widths):
        _para(c, off + 7, top - 19, h, width - 10, 7.3, 8, WHITE, True, 2)
        off += width
    y = top - 31
    for idx, cells in enumerate(rows):
        c.setFillColor(PALE if idx % 2 == 0 else WHITE)
        c.rect(x, y - row_h, table_w, row_h, fill=1, stroke=0)
        off = x
        for cell, width, size in zip(cells, widths, sizes):
            text = str(cell if cell is not None else "—")
            lines = _lines(text, width - 13, size)[:2]
            for j, line in enumerate(lines):
                _text(c, off + 7, y - 14 - j * 10, line, size, INK,
                      bold=(j == 0 and idx == 0 and off == x))
            off += width
        y -= row_h
        c.setStrokeColor(BORDER)
        c.setLineWidth(.3)
        c.line(x, y, x + table_w, y)
    return y


def _data(data):
    monthly = data.get("monthly") or {}
    specialty = [dict(s) for s in data.get("monthly_progress_by_specialty") or []]
    if specialty:
        total = sum(_n(row.get("total_ot")) for row in specialty)
        completed = sum(_n(row.get("completed_ot")) for row in specialty)
        planned_unique = sum(_n(row.get("scheduled_unique")) for row in specialty)
        planned_done = sum(_n(row.get("scheduled_completed")) for row in specialty)
        unplanned_done = sum(_n(row.get("unplanned_completed")) for row in specialty)
        hh_total = sum(_n(row.get("total_hh")) for row in specialty)
        hh_done = sum(_n(row.get("completed_hh")) for row in specialty)
        repeated = sum(_n(row.get("scheduled_reprogrammed_assignments")) for row in specialty)
    else:
        # Compatibilidad con reportes anteriores a la cartera por especialidad.
        total = _n(monthly.get("programmed"))
        completed = _n(monthly.get("finalized"))
        planned_unique = _n(monthly.get("programmed"))
        planned_done = _n(monthly.get("finalized"))
        unplanned_done = 0
        hh_total = _n((data.get("weekly_totals") or {}).get("hh_programmed"))
        hh_done = _n((data.get("weekly_totals") or {}).get("hh_finalized"))
        repeated = 0
    return {
        "specialties": specialty,
        "total": int(total), "completed": int(completed),
        "planned_unique": int(planned_unique), "planned_done": int(planned_done),
        "unplanned_done": int(unplanned_done), "hh_total": hh_total,
        "hh_done": hh_done, "repeated": int(repeated),
        "general_pct": _percent(completed, total),
        "program_pct": _percent(planned_done, planned_unique),
        "hh_pct": _percent(hh_done, hh_total),
        "complete": bool(monthly.get("all_weeks_closed")),
        "weeks_closed": int(monthly.get("weeks_closed") or 0),
        "weeks_total": int(monthly.get("weeks_total") or 0),
        "pending": int(monthly.get("pending") or 0),
        "missing": int(monthly.get("not_found") or 0),
        "unchecked": int(monthly.get("unchecked") or 0),
        "pmp_without_programming": int(monthly.get("not_programmed") or 0),
        "inherited_backlog": int(monthly.get("from_prior_backlog") or 0),
        "monthly": monthly,
    }


def _summary_page(c, m, code, issue):
    _page(c, 2, "01 / Visión general", "Resumen ejecutivo",
          "Cartera mensual de mantenimiento · Planta Barranquilla", code, issue)
    y = 644
    _section(c, y, "Alcance en cifras")
    gap = 10
    tw = (CONTENT_W - gap * 2) / 3
    _tile(c, LEFT, 540, tw, "OT en cartera", _num(m["total"]),
          "PMP y backlog del período", NAVY)
    _tile(c, LEFT + tw + gap, 540, tw, "OT finalizadas", _num(m["completed"]),
          "Dentro y fuera del plan", TEAL)
    _tile(c, LEFT + 2 * (tw + gap), 540, tw, "Cumplimiento general",
          _pct(m["general_pct"]), "Sobre OT únicas del mes", BLUE)

    _section(c, 508, "Resultados de la ejecución")
    _tile(c, LEFT, 402, tw, "OT programadas únicas", _num(m["planned_unique"]),
          "Sin contar reprogramaciones", NAVY)
    _tile(c, LEFT + tw + gap, 402, tw, "Programadas finalizadas", _num(m["planned_done"]),
          "Cierre / seguimiento", TEAL)
    _tile(c, LEFT + 2 * (tw + gap), 402, tw, "Fuera de programación",
          _num(m["unplanned_done"]), "OT únicas finalizadas", AMBER)

    _section(c, 376, "Lectura gerencial")
    _rounded(c, LEFT, 227, CONTENT_W, 132, PALE, BORDER, 9)
    narrative = (
        f"Durante {m['monthly'].get('periodo', 'el período analizado')} se consolidaron "
        f"{_num(m['total'])} órdenes únicas de la cartera mensual. "
        f"Al corte se registraron {_num(m['completed'])} OT finalizadas, "
        f"equivalentes a {_pct(m['general_pct'])} de cumplimiento general. "
        f"De ellas, {_num(m['planned_done'])} corresponden a ejecución programada y "
        f"{_num(m['unplanned_done'])} a finalizaciones fuera de programación."
    )
    # No usar un campo inexistente del período como fuente de la fecha.
    narrative = narrative.replace("Durante el período analizado se", "En el período analizado se")
    _para(c, LEFT + 17, 326, narrative, CONTENT_W - 34, 10, 16, INK, max_lines=7)
    _section(c, 199, "Criterios de interpretación")
    _para(c, LEFT, 177,
          "El resultado general se calcula por OT diferentes de la cartera PMP + backlog. "
          "Una misma OT reprogramada en varias semanas se cuenta una sola vez. "
          "Las H-H son estimaciones asociadas a las actividades, no horas reales trabajadas.",
          CONTENT_W, 9.1, 15, MUTED, max_lines=5)
    if not m["complete"]:
        _text(c, LEFT, 83, "INFORME PARCIAL: EXISTEN PROGRAMACIONES SIN CIERRE.",
              9, AMBER, True)
    c.showPage()


def _balance_page(c, m, code, issue):
    _page(c, 3, "02 / Resultados", "Balance mensual de OT",
          "Dos indicadores complementarios, ambos calculados sobre órdenes únicas.", code, issue)
    _ring(c, 176, 549, 66, m["general_pct"], "GENERAL",
          f"{_num(m['completed'])} / {_num(m['total'])} OT", BLUE)
    _ring(c, 423, 549, 66, m["program_pct"], "PROGRAMADAS",
          f"{_num(m['planned_done'])} / {_num(m['planned_unique'])} OT", TEAL)

    _section(c, 421, "Comparativo por especialidad")
    rows = []
    for s in m["specialties"]:
        rows.append([
            NAMES.get(s.get("especialidad"), s.get("name", "")),
            _num(s.get("total_ot")), _num(s.get("completed_ot")),
            _pct(s.get("progress_ot_pct")),
            f"{_num(s.get('scheduled_completed'))} / {_num(s.get('scheduled_unique'))}",
            _pct(s.get("scheduled_progress_ot_pct")),
        ])
    if rows:
        _table(c, LEFT, 402, [100, 68, 81, 67, 115, CONTENT_W - 431],
               ["ESPECIALIDAD", "OT CARTERA", "FINALIZ.", "GENERAL",
                "PROGR. ÚNICAS", "PROGR. %"], rows, 39, [8, 9, 9, 8.5, 8.3, 8.5])
    else:
        _text(c, LEFT, 363, "No hay desagregación por especialidad disponible.", 10, MUTED)

    _section(c, 183, "Interpretación del indicador")
    _para(c, LEFT, 161,
          "El cumplimiento general incluye las OT finalizadas fuera de programación. "
          "El cumplimiento programado utiliza solo las OT programadas diferentes y "
          "excluye duplicaciones causadas por el arrastre entre semanas. "
          "Por esta razón, ambos resultados pueden diferir.",
          CONTENT_W, 9.1, 15, INK, max_lines=5)
    c.showPage()


def _group_weeks(data):
    grouped = defaultdict(lambda: {"assigned": 0, "done": 0, "closed": True, "hh": 0})
    for w in data.get("weeks") or []:
        label = (str(w.get("week_from") or "")[:10], str(w.get("week_to") or "")[:10])
        g = grouped[label]
        g["assigned"] += int(_n(w.get("programmed")))
        g["done"] += int(_n(w.get("finalized")))
        g["hh"] += _n(w.get("hh_programmed"))
        g["closed"] = g["closed"] and w.get("estado") == "CERRADA"
    return [(key, val) for key, val in sorted(grouped.items())]


def _weekly_page(c, data, code, issue):
    _page(c, 4, "03 / Ejecución semanal", "Evolución de la programación",
          "Cortes semanales registrados. La misma OT puede aparecer en más de una semana.", code, issue)
    grouped = _group_weeks(data)
    _section(c, 641, "Programadas y finalizadas por corte")
    top = 614
    max_events = max([g["assigned"] for _, g in grouped] or [1])
    for idx, ((from_day, to_day), g) in enumerate(grouped[:6]):
        y = top - idx * 57
        _text(c, LEFT, y, f"{from_day[5:]} al {to_day[5:]}", 9, NAVY, True)
        _text(c, RIGHT, y, f"{_num(g['done'])} / {_num(g['assigned'])}", 9, INK, True, "right")
        bar_width = CONTENT_W - 110
        c.setFillColor(LIGHT)
        c.roundRect(LEFT, y - 24, bar_width, 12, 6, stroke=0, fill=1)
        width = bar_width * min(1., g["assigned"] / max_events)
        if width:
            c.setFillColor(colors.HexColor("#A8CEDB"))
            c.roundRect(LEFT, y - 24, width, 12, 5, stroke=0, fill=1)
        done_width = bar_width * min(1., g["done"] / max_events)
        if done_width:
            c.setFillColor(TEAL)
            c.roundRect(LEFT, y - 24, done_width, 12, 5, stroke=0, fill=1)
        _text(c, RIGHT, y - 22, "CERRADA" if g["closed"] else "ABIERTA",
              7.3, TEAL if g["closed"] else AMBER, True, "right")

    table_top = 607 - min(len(grouped), 6) * 57 - 15
    _section(c, table_top + 18, "Cuadro de seguimiento semanal")
    rows = [
        [f"{from_day[5:]} al {to_day[5:]}", _num(g["assigned"]), _num(g["done"]),
         _pct(_percent(g["done"], g["assigned"])),
         "Cerrada" if g["closed"] else "Abierta"]
        for (from_day, to_day), g in grouped[:6]
    ]
    if rows:
        _table(c, LEFT, table_top,
               [147, 106, 108, 92, CONTENT_W - 453],
               ["CORTE", "ASIGNACIONES", "FINALIZADAS", "OT %", "ESTADO"],
               rows, 26, [8, 8.5, 8.5, 8.5, 8])
    _para(c, LEFT, 103,
          "Nota: el cuadro mide eventos de programación por semana. "
          "No equivale al número de OT únicas de la cartera mensual y "
          "no debe utilizarse como denominador del cumplimiento general.",
          CONTENT_W, 8.6, 13, MUTED, max_lines=3)
    c.showPage()


def _specialty_page(c, m, code, issue):
    _page(c, 5, "04 / Especialidades", "Desempeño por especialidad",
          "Avance de la cartera, programación única y H-H estimadas de OT finalizadas.", code, issue)
    specs = m["specialties"][:4]
    for i, s in enumerate(specs):
        column = i % 2
        row = i // 2
        x = LEFT + column * (CONTENT_W / 2 + 6)
        width = CONTENT_W / 2 - 6
        y = 451 - row * 224
        _rounded(c, x, y, width, 195, WHITE, BORDER, 10)
        _text(c, x + 14, y + 171, NAMES.get(s.get("especialidad"), s.get("name", "")),
              12, NAVY, True)
        _text(c, x + 14, y + 133, _pct(s.get("progress_ot_pct")), 24, BLUE, True)
        _text(c, x + 14, y + 114,
              f"{_num(s.get('completed_ot'))} de {_num(s.get('total_ot'))} OT de la cartera",
              8.2, INK)
        _progress(c, x + 14, y + 63, width - 28, "OT programadas únicas",
                  s.get("scheduled_progress_ot_pct"), color=TEAL)
        _text(c, x + 14, y + 37,
              f"{_num(s.get('scheduled_completed'))} de {_num(s.get('scheduled_unique'))} OT",
              8.2, MUTED)
        _text(c, x + 14, y + 18,
              f"H-H est.: {_num(s.get('completed_hh'),1)} de {_num(s.get('total_hh'),1)}",
              8.2, INK, True)
    if not specs:
        _rounded(c, LEFT, 428, CONTENT_W, 140, PALE, BORDER)
        _para(c, LEFT + 18, 520,
              "No se dispone de datos por especialidad para este mes. "
              "El consolidado general se conserva en las páginas previas.",
              CONTENT_W - 36, 11, 16)
    _section(c, 177, "Nota de lectura")
    _para(c, LEFT, 154,
          "Las H-H son valores estimados según la orden y la planeación. "
          "Un porcentaje de cumplimiento bajo no implica por sí solo una "
          "causa operativa; las desviaciones deben revisarse con mantenimiento.",
          CONTENT_W, 9, 14, MUTED, max_lines=4)
    c.showPage()


def _backlog_page(c, data, m, code, issue):
    _page(c, 6, "05 / Pendientes", "Backlog y desviaciones",
          "Saldo de cierre, cartera no programada y actividades que requieren seguimiento.",
          code, issue)
    gap = 12
    tw = (CONTENT_W - gap) / 2
    _tile(c, LEFT, 535, tw, "Pendientes en último cierre", _num(m["pending"]),
          "Último estado de OT programadas", AMBER, 88)
    _tile(c, LEFT + tw + gap, 535, tw, "No encontradas", _num(m["missing"]),
          "OT sin coincidencia en cierre", BLUE, 88)
    _tile(c, LEFT, 430, tw, "PMP sin programar", _num(m["pmp_without_programming"]),
          "No equivale a backlog final", NAVY, 88)
    _tile(c, LEFT + tw + gap, 430, tw, "Backlog de período previo", _num(m["inherited_backlog"]),
          "OT únicas heredadas programadas", TEAL, 88)

    _section(c, 403, "OT pendientes y no conciliadas: muestra de seguimiento")
    unresolved = data.get("unresolved") or []
    rows = []
    for row in unresolved[:8]:
        rows.append([
            row.get("numero_ot") or "SIN OT",
            NAMES.get(row.get("especialidad"), row.get("especialidad", "—")),
            row.get("activo") or "—",
            row.get("resultado") or "PENDIENTE",
            _num(row.get("hh_estimada"), 1),
        ])
    if rows:
        _table(c, LEFT, 382, [106, 116, 147, 93, CONTENT_W - 462],
               ["OT", "ESPECIALIDAD", "EQUIPO", "RESULTADO", "H-H EST."],
               rows, 28, [7.6, 7.8, 7.4, 7.5, 8])
        if len(unresolved) > len(rows):
            _text(c, LEFT, 116,
                  f"Muestra de {len(rows)} de {_num(len(unresolved))} OT; consultar el detalle completo en la aplicación.",
                  8, MUTED)
    else:
        _rounded(c, LEFT, 261, CONTENT_W, 112, PALE, BORDER)
        _para(c, LEFT + 16, 328,
              "No hay OT pendientes o sin conciliar registradas en el "
              "detalle de último cierre incluido en esta consulta.",
              CONTENT_W - 32, 10, 16)

    _para(c, LEFT, 98,
          "Los pendientes del último cierre, el PMP sin programar y el backlog heredado "
          "son universos distintos. No deben sumarse directamente ni interpretarse "
          "como el backlog activo total de la base de datos.",
          CONTENT_W, 8.4, 12, MUTED, max_lines=3)
    c.showPage()


def _conclusions_page(c, data, m, code, issue, month, year):
    _page(c, 7, "06 / Dirección y control", "Conclusiones gerenciales",
          "Hallazgos cuantitativos y acciones sugeridas para el siguiente ciclo.",
          code, issue)
    _section(c, 646, "Mensajes principales")
    specs = [s for s in m["specialties"] if _n(s.get("total_ot"))]
    max_gap = max(specs, key=lambda r: _n(r.get("total_ot")) - _n(r.get("completed_ot")), default=None)
    highest_unplanned = max(specs, key=lambda r: _n(r.get("unplanned_completed")), default=None)
    findings = [
        f"El período registra {_num(m['completed'])} OT finalizadas de {_num(m['total'])} "
        f"OT únicas de cartera ({_pct(m['general_pct'])}).",
        f"Las OT programadas únicas finalizadas fueron {_num(m['planned_done'])} de "
        f"{_num(m['planned_unique'])} ({_pct(m['program_pct'])}). "
        f"Se evitaron {_num(m['repeated'])} registros adicionales por reprogramación.",
    ]
    if max_gap:
        gap = int(_n(max_gap.get("total_ot")) - _n(max_gap.get("completed_ot")))
        findings.append(
            f"{NAMES.get(max_gap.get('especialidad'), max_gap.get('name', 'La especialidad'))} "
            f"presenta {_num(gap)} OT de cartera sin finalización acreditada en el período."
        )
    if highest_unplanned and _n(highest_unplanned.get("unplanned_completed")):
        findings.append(
            f"{NAMES.get(highest_unplanned.get('especialidad'), highest_unplanned.get('name', 'La especialidad'))} "
            f"concentra {_num(highest_unplanned.get('unplanned_completed'))} "
            "finalizaciones fuera de programación registradas."
        )
    cursor = 621
    for i, f in enumerate(findings[:4], 1):
        _text(c, LEFT, cursor, f"{i:02d}", 11, TEAL, True)
        cursor = _para(c, LEFT + 30, cursor, f, CONTENT_W - 30, 9.4, 14, INK, max_lines=3) - 13

    _section(c, 420, "Plan de acción recomendado")
    actions = [
        ["01", "Revisar la cartera sin finalización acreditada y priorizar el próximo corte.",
         "Mantenimiento", "Programación ajustada"],
        ["02", "Analizar las OT ejecutadas fuera de programación y su clasificación.",
         "Planeación", "Listado conciliado"],
        ["03", "Evaluar las reprogramaciones para mejorar la estabilidad del plan.",
         "Planeación / Ejecución", "Causales registradas"],
    ]
    _table(c, LEFT, 402, [36, 257, 105, CONTENT_W - 398],
           ["#", "ACCIÓN SUGERIDA", "RESP. SUGERIDO", "EVIDENCIA"],
           actions, 51, [8, 8.2, 7.7, 7.5])
    _section(c, 195, "Alcance y trazabilidad")
    _para(c, LEFT, 173,
          "Fuente: plataforma PROGRAMACIÓN TEAM FOOD; base mensual PMP, "
          "backlog, seguimiento y cierres semanales registrados. "
          "Los porcentajes se calcularon por OT distintas en el mes. "
          "Las cifras de H-H son estimadas, no horas reales ejecutadas. "
          "Este informe no acredita aprobación de recomendaciones ni cierre formal mensual.",
          CONTENT_W, 8.8, 13, MUTED, max_lines=6)
    _text(c, LEFT, 84, "ELABORADO POR C.E.K GLOBAL INSPECTION SERVICES S.A.S.",
          8.3, NAVY, True)
    c.showPage()


def render_monthly_executive_pdf(data: dict[str, Any], year: int, month: int) -> tuple[bytes, str]:
    if not 1 <= month <= 12:
        raise ValueError("Mes fuera de rango")
    if not data.get("weeks"):
        raise ValueError("No hay programaciones para generar el reporte")

    issue_date = datetime.now(ZoneInfo("America/Bogota")).strftime("%d/%m/%Y")
    code = f"CEK-MTTO-{year}-{month:02d}"
    metrics = _data(data)
    output = BytesIO()
    c = canvas.Canvas(output, pagesize=A4, pageCompression=0, invariant=1)
    c.setTitle(f"Informe gerencial de mantenimiento - {MONTHS[month]} {year}")
    c.setAuthor("C.E.K Global Inspection Services S.A.S.")
    c.setSubject("Consolidado mensual de programación, cumplimiento y backlog")

    _cover(c, year, month, issue_date, code,
           _load_logo("cek_logo.b64"), _load_logo("team_foods_logo.b64"),
           metrics["complete"])
    _summary_page(c, metrics, code, issue_date)
    _balance_page(c, metrics, code, issue_date)
    _weekly_page(c, data, code, issue_date)
    _specialty_page(c, metrics, code, issue_date)
    _backlog_page(c, data, metrics, code, issue_date)
    _conclusions_page(c, data, metrics, code, issue_date, month, year)
    c.save()
    return output.getvalue(), f"informe_gerencial_cierre_mensual_{year}_{month:02d}.pdf"
