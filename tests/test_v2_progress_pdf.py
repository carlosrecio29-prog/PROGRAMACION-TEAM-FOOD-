from datetime import date

from backend.services import v2_progress_service as progress


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


def test_pdf_monthly_and_weekly_are_real_pdf_bytes(monkeypatch):
    monkeypatch.setattr(progress, "get_progress", lambda year, month: fake_progress())
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
