"""Dependency-free PDF renderer for Vercel runtimes without ReportLab.

Used only when the standard ReportLab report is unavailable. Never alters data.
"""
from __future__ import annotations

from datetime import date
from typing import Any


def _safe(value: Any) -> bytes:
    text = str(value if value is not None else "")
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text.encode("cp1252", "replace")


class _PDF:
    WIDTH, HEIGHT = 842, 595

    def __init__(self):
        self.pages: list[bytes] = []
        self.parts: list[bytes] = []
        self.y = 0
        self.start_page()

    def start_page(self):
        if self.parts:
            self.pages.append(b"\n".join(self.parts))
        self.parts = [b"0.10 0.21 0.36 rg 0.10 0.21 0.36 RG"]
        self.y = 556
        self.rect(0, 572, 842, 23, (0.10, 0.21, 0.36))
        self.text(31, 580, "TEAM FOODS  |  C.E.K GLOBAL INSPECTION", 10, white=True)

    def text(self, x: float, y: float, value: Any, size=9, *, white=False):
        color = b"1 1 1 rg" if white else b"0.10 0.21 0.36 rg"
        self.parts.append(
            color + b" BT /F1 " + str(size).encode() + b" Tf "
            + f"1 0 0 1 {x:.1f} {y:.1f} Tm ".encode()
            + b"(" + _safe(value) + b") Tj ET"
        )

    def rect(self, x, y, width, height, color):
        self.parts.append(("%.3f %.3f %.3f rg %.1f %.1f %.1f %.1f re f"
                           % (*color, x, y, width, height)).encode())

    def line(self, text, size=9, gap=15):
        if self.y < 55:
            self.start_page()
        self.text(31, self.y, text, size)
        self.y -= gap

    def wrap(self, label, *, max_len=124, gap=13):
        s = str(label)
        while len(s) > max_len:
            idx = s.rfind(" ", 0, max_len)
            if idx < 20:
                idx = max_len
            self.line(s[:idx], gap=gap)
            s = s[idx:].lstrip()
        self.line(s, gap=gap)

    def finish(self):
        self.pages.append(b"\n".join(self.parts))
        objs: list[bytes] = []
        def add(obj):
            objs.append(obj)
            return len(objs)
        font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        pages_ref = add(b"")
        page_refs = []
        for stream in self.pages:
            content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
            page_refs.append(add(
                b"<< /Type /Page /Parent " + str(pages_ref).encode() + b" 0 R "
                b"/MediaBox [0 0 842 595] /Resources << /Font << /F1 "
                + str(font).encode() + b" 0 R >> >> "
                + b"/Contents " + str(content).encode() + b" 0 R >>"
            ))
        objs[pages_ref-1] = b"<< /Type /Pages /Count %d /Kids [%s] >>" % (
            len(page_refs), b" ".join(f"{r} 0 R".encode() for r in page_refs))
        root = add(b"<< /Type /Catalog /Pages " + str(pages_ref).encode() + b" 0 R >>")
        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, obj in enumerate(objs, 1):
            offsets.append(len(output))
            output.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
        xref = len(output)
        output.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode())
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode())
        output.extend(
            b"trailer\n<< /Size " + str(len(objs)+1).encode()
            + b" /Root " + str(root).encode() + b" 0 R >>\n"
            + b"startxref\n" + str(xref).encode() + b"\n%%EOF\n")
        return bytes(output)


def render_progress_fallback(data: dict[str, Any], year: int, month: int,
                             programming_id: int | None = None) -> tuple[bytes, str]:
    weeks = data["weeks"]
    kind = "mensual"
    if programming_id is not None:
        weeks = [w for w in weeks if w["programming_id"] == programming_id]
        if not weeks:
            raise ValueError("La programación no corresponde al mes indicado")
        kind = "semanal"
    if not weeks:
        raise ValueError("No hay programaciones para generar el reporte")
    pdf = _PDF()
    pdf.line("INFORME DE CIERRE " + ("MENSUAL" if kind == "mensual" else "SEMANAL"), 18, 30)
    pdf.line(f"Periodo: {year}-{month:02d}", 11, 20)
    if kind == "mensual":
        m = data["monthly"]
        pdf.wrap(f"PROGRAMACIONES CERRADAS: {m['weeks_closed']} de {m['weeks_total']}. "
                 f"OT distintas: {m['programmed']}. Finalizadas: {m['finalized']}. "
                 f"Pendientes: {m['pending']}. No encontradas: {m['not_found']}. "
                 f"Sin verificar: {m['unchecked']}. PMP mantenimiento: {m['pmp_count']}.")
        if not m["all_weeks_closed"]:
            pdf.line("INFORME PARCIAL: hay programaciones sin cierre.", 10)
    else:
        w = weeks[0]
        pdf.line(f"{w['week_from']} al {w['week_to']}  |  {w['especialidad']}", 11)
    if any(w["estado"] == "CERRADA" and w["semana_fin"] > date.today() for w in weeks):
        pdf.line("CIERRE ANTICIPADO / PRUEBA: incluye semanas futuras.", 10, 19)
    pdf.y -= 12
    pdf.line("EVOLUCION SEMANAL: OT PROGRAMADAS / FINALIZADAS", 12, 23)
    max_total = max(w["programmed"] for w in weeks) or 1
    for w in weeks:
        if pdf.y < 105:
            pdf.start_page()
        label = f"{w['week_from'][5:]} - {w['week_to'][5:]} {w['especialidad']}"
        pdf.line(label + f"   OT: {w['finalized']}/{w['programmed']}   "
                 + f"HH est. finalizadas: {w['hh_finalized']:.2f}/{w['hh_programmed']:.2f}", 9, 17)
        y = pdf.y + 3
        pdf.rect(31, y, 350 * w["programmed"] / max_total, 7, (.75, .84, .92))
        pdf.rect(31, y, 350 * w["finalized"] / max_total, 7, (.18, .46, .71))
        pdf.y -= 17
    pdf.y -= 9
    pdf.wrap("CRITERIO: cada semana cuenta sus OT programadas. El mes cuenta cada OT una vez, "
             "segun la ultima semana programada. Las HH son estimaciones del plan, no horas reales.", gap=15)
    if kind == "mensual" and data.get("unresolved"):
        pdf.start_page()
        pdf.line("PENDIENTES DEL ULTIMO CIERRE DEL MES", 15, 28)
        pdf.line("OT                         ESPECIALIDAD   ESTADO                  HH EST.", 9, 18)
        for row in data["unresolved"]:
            if pdf.y < 65:
                pdf.start_page()
            pdf.line(
                f"{row['numero_ot'][:26]:26} "
                f"{row['especialidad'][:10]:10} "
                f"{row['resultado'][:20]:20} "
                f"{row['hh_estimada']:.2f}", 9, 13)
    filename = (f"informe_{kind}_mtto_{year}_{month:02d}"
                + (f"_{programming_id}" if programming_id is not None else "") + ".pdf")
    return pdf.finish(), filename
