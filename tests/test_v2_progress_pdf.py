from datetime import date

from backend.services import v2_progress_service as progress
from backend.services import v2_closure_service as closure
from backend.services import v2_week_tracking_service as tracking


def fake_progress():
    headers = [
        {"id": 41, "semana_inicio": date(2026, 9, 3),
         "semana_fin": date(2026, 9, 9), "especialidad": "ELE",
         "estado": "CERRADA"},
        {"id": 42, "semana_inicio": date(2026, 9, 10),
         "semana_fin": date(2026, 9, 16), "especialidad": "ELE",
         "estado": "CERRADA"},
    ]
    items = [
        {"programacion_id": 41, "orden_mantenimiento_id": 1,
         "hh_programadas": 2, "finalizado": False, "estado_cierre": "ABIERTO",
         "origen_backlog": False, "numero_ot": "OT-1",
         "activo_codigo": "BA-TEST", "plan_clave_software": "PLAN UNO",
         "especialidad": "ELE", "periodo": date(2026, 9, 1)},
        {"programacion_id": 42, "orden_mantenimiento_id": 1,
         "hh_programadas": 2, "finalizado": True, "estado_cierre": "FINALIZADO",
         "origen_backlog": True, "numero_ot": "OT-1",
         "activo_codigo": "BA-TEST", "plan_clave_software": "PLAN UNO",
         "especialidad": "ELE", "periodo": date(2026, 9, 1)},
        {"programacion_id": 42, "orden_mantenimiento_id": 2,
         "hh_programadas": 3, "finalizado": False, "estado_cierre": "ABIERTO",
         "origen_backlog": False, "numero_ot": "OT-2",
         "activo_codigo": "BA-TEST", "plan_clave_software": "PLAN DOS",
         "especialidad": "ELE", "periodo": date(2026, 9, 1)},
    ]
    return {"year": 2026, "month": 9,
            **progress.aggregate_progress(headers, items, 12, date(2026, 9, 1))}


def _fake_week_closure(programming_id):
    return {"rows": [
        {"numero_ot": "OT-1", "activo_codigo": "BA-TEST",
         "plan_trabajo": "PLAN UNO", "estado_cierre": "FINALIZADO",
         "finalizado": True, "hh_programadas": 2},
        {"numero_ot": "OT-2", "activo_codigo": "BA-TEST",
         "plan_trabajo": "PLAN DOS", "estado_cierre": "ABIERTO",
         "finalizado": False, "hh_programadas": 3},
    ]}





def _fake_week_tracking(programming_id):
    return {
        "unplanned": {
            "rows": [
                {
                    "numero_ot": "OT-NP-1",
                    "activo_codigo": "BA-NP",
                    "plan_trabajo": "PLAN NO PROGRAMADO",
                    "origen": "PMP_NO_PROGRAMADO",
                    "fecha_fin_orden": "2026-09-12T15:30:00",
                    "hh_estimada": 1.5,
                }
            ]
        }
    }

def test_pdf_monthly_and_weekly_are_real_pdf_bytes(monkeypatch):
    monkeypatch.setattr(progress, "get_progress", lambda year, month: fake_progress())
    monkeypatch.setattr(closure, "get_week_closure", _fake_week_closure)
    monkeypatch.setattr(tracking, "get_week_tracking", _fake_week_tracking)
    monthly, name = progress.export_progress_pdf(2026, 9)
    assert monthly.startswith(b"%PDF-")
    assert len(monthly) > 1000
    assert name.endswith(".pdf")
    weekly, weekly_name = progress.export_progress_pdf(2026, 9, 42)
    assert weekly.startswith(b"%PDF-")
    assert len(weekly) > 1000
    assert "42.pdf" in weekly_name


def test_pdf_unknown_week_rejected(monkeypatch):
    import pytest

    monkeypatch.setattr(progress, "get_progress", lambda year, month: fake_progress())
    with pytest.raises(ValueError, match="no corresponde"):
        progress.export_progress_pdf(2026, 9, 999)


def test_pdf_falls_back_if_reportlab_missing(monkeypatch):
    import builtins

    monkeypatch.setattr(progress, "get_progress", lambda year, month: fake_progress())
    monkeypatch.setattr(closure, "get_week_closure", _fake_week_closure)
    monkeypatch.setattr(tracking, "get_week_tracking", _fake_week_tracking)
    original_import = builtins.__import__

    def without_reportlab(name, *args, **kwargs):
        if name == "reportlab" or name.startswith("reportlab."):
            raise ModuleNotFoundError("No module named 'reportlab'", name="reportlab")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_reportlab)
    for programming_id in (None, 42):
        content, filename = progress.export_progress_pdf(2026, 9, programming_id)
        assert content.startswith(b"%PDF-1.4")
        assert content.rstrip().endswith(b"%%EOF")
        assert len(content) > 1000
        assert filename.endswith(".pdf")


def test_visual_pdf_contains_kpi_charts_and_technical_sections(monkeypatch):
    monkeypatch.setattr(progress, "get_progress", lambda year, month: fake_progress())
    monkeypatch.setattr(closure, "get_week_closure", _fake_week_closure)
    monkeypatch.setattr(tracking, "get_week_tracking", _fake_week_tracking)
    monthly, _ = progress.export_progress_pdf(2026, 9)
    weekly, _ = progress.export_progress_pdf(2026, 9, 42)
    for document in (monthly, weekly):
        assert document.startswith(b"%PDF-1.4")
        assert document.rstrip().endswith(b"%%EOF")
        assert b"INDICADORES PRINCIPALES" in document
        assert b"CUMPLIMIENTO OT" in document
        assert b"HH DE OT CERRADAS" in document
        assert document.count(b"/Type /Page ") >= 2
    assert b"COMPARATIVO POR ESPECIALIDAD" in monthly
    assert b"DETALLE" in monthly and b"OT-2" in monthly
    assert b"DETALLE" in weekly and b"OT-1" in weekly
    assert b"OT FINALIZADAS NO PROGRAMADAS" in weekly
    assert b"OT NO PROGRAMADAS REALIZADAS" in weekly
    assert b"OT-NP-1" in weekly
    assert weekly.rfind(b"OT FINALIZADAS NO PROGRAMADAS") > weekly.rfind(b"DETALLE")


def test_first_page_kpis_are_compact_and_without_removed_notes():
    source = (ROOT / "backend/services/v2_pdf_fallback.py").read_text()
    summary_block = source[source.index("def _summary"):source.index("def _kpi_note")]
    assert '("No encontradas"' not in summary_block
    assert "Suma de semanas; estimadas" not in summary_block
    assert "Estimadas; no horas reales" not in summary_block
    assert summary_block.count('("') >= 8


def test_weekly_pdf_removed_explanatory_labels_and_bar():
    source = (ROOT / "backend/services/v2_pdf_fallback.py").read_text()
    assert "Cada tarjeta refleja datos verificados en los cierres" not in source
    assert "Sobre HH estimadas" not in source
    assert "HH estimadas; no horas reales" not in source
    weekly_block = source[source.index("    else:"):source.index('    kind="mensual"')]
    assert 'pdf.section("OT programadas y finalizadas")' not in weekly_block
    assert 'pdf.section("Criterios del informe")' not in weekly_block
