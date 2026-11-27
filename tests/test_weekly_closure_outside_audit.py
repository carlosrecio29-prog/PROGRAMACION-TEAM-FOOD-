"""Regresiones: el cierre incluye OT finalizadas no programadas sin duplicarlas."""
from pathlib import Path

from backend.services.v2_pdf_fallback import _weekly_outside_audit_table


class _PDFProbe:
    def __init__(self):
        self.calls = []
        self.y = 500

    def new_page(self):
        self.calls.append(("page",))

    def section(self, *args):
        self.calls.append(("section", args))

    def cards(self, cards, cols=4):
        self.calls.append(("cards", cards))

    def paragraph(self, text, **kwargs):
        self.calls.append(("paragraph", text))

    def table(self, columns, rows, widths, **kwargs):
        self.calls.append(("table", columns, rows, widths, kwargs))


def test_pdf_weekly_outside_uses_detection_without_inventing_hh():
    pdf = _PDFProbe()
    audit = {
        "fuente": "CAMBIOS_GOOGLE_SHEETS",
        "total": 2,
        "fuera_del_mes": 1,
        "programadas_otra_semana": 1,
        "posteriores_al_corte": 1,
        "rows": [
            {"numero_ot": "OT-100-26", "area_codigo": "EM",
             "activo_codigo": "BA-EM-1", "plan_trabajo": "INSPECCION",
             "programada_alguna_vez": False,
             "detectado_en": "2026-11-24T11:03:00+00:00"},
            {"numero_ot": "OT-101-26", "area_codigo": "JB",
             "activo_codigo": "BA-JB-2", "plan_trabajo": "REVISION",
             "programada_alguna_vez": True,
             "detectado_en": "2026-11-26T11:04:00+00:00"},
        ],
    }
    _weekly_outside_audit_table(pdf, audit)
    assert sum(call[0] == "page" for call in pdf.calls) == 1
    cards = next(call[1] for call in pdf.calls if call[0] == "cards")
    assert len(cards) == 1
    assert cards[0][1] == "2"
    assert cards[0][0] == "TOTAL OT FUERA DE PROGRAMACION"
    table = next(call for call in pdf.calls if call[0] == "table")
    assert table[1] == ["OT", "AREA", "EQUIPO", "PLAN DE TRABAJO", "PROGRAMACION", "DETECTADA"]
    assert len(table[2]) == 2
    assert table[2][0][0] == "OT-100-26"
    assert table[2][1][4] == "OTRA SEMANA"
    assert all("HH" not in name for name in table[1])
    assert any("NO acredita" in call[1] for call in pdf.calls if call[0] == "paragraph")


def test_weekly_closure_screen_and_pdf_share_audit_api():
    root = Path(__file__).resolve().parents[1]
    closure = (root / "frontend/src/components/WeeklyClosure.jsx").read_text(encoding="utf-8")
    report = (root / "backend/services/v2_progress_service.py").read_text(encoding="utf-8")
    renderer = (root / "backend/services/v2_pdf_fallback.py").read_text(encoding="utf-8")
    assert "getWeeklyOutsideFinalizations(" in closure
    assert "outsideFinalizations.total" in closure
    assert "outsideFinalizations.programadas_otra_semana" not in closure
    assert "outsideFinalizations.fuera_del_mes" not in closure
    assert "outsideFinalizations.rows" in closure
    assert "No se suman a las OT programadas" in closure
    assert "weekly_finalized_outside_programming(" in report
    assert "weekly_outside_audit=weekly_outside_audit" in report
    assert "if weekly_outside_audit and weekly_outside_audit.get" in renderer
    assert "_weekly_outside_audit_table(pdf,weekly_outside_audit)" in renderer
