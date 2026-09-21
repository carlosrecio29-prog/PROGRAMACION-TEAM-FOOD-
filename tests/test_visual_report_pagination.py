"""Check self-contained visual PDF before release, independent of ReportLab."""
from backend.services.v2_pdf_fallback import _PDF, render_progress_fallback


def test_vector_engine_paginates_large_technical_tables():
    document = _PDF("INFORME DE CIERRE SEMANAL", "SEPTIEMBRE 2026", "SEMANAL")
    document.section("Detalle técnico de órdenes")
    document.table(
        ["OT", "ESPECIALIDAD", "EQUIPO"],
        [[f"OT-{n:05d}", "MEC", "BA-PRUEBA"] for n in range(222)],
        [120, 160, 499], repeat_title="Detalle (continuación)",
    )
    output = document.finish()
    assert output.startswith(b"%PDF-1.4")
    assert output.rstrip().endswith(b"%%EOF")
    assert output.count(b"/Type /Page ") >= 5
    assert b"OT-00221" in output
    assert b"/BaseFont /Helvetica-Bold" in output


def test_render_has_vector_graphs_and_branding():
    weekly = {
        "programming_id": 7, "week_from": "2026-09-03",
        "week_to": "2026-09-09", "semana_fin": __import__("datetime").date(2026, 9, 9),
        "especialidad": "MEC", "estado": "CERRADA", "programmed": 81,
        "finalized": 30, "pending": 50, "not_found": 1,
        "unchecked": 0, "hh_programmed": 160.0, "hh_finalized": 85.0,
    }
    monthly = {
        "programmed": 81, "finalized": 30, "pending": 50, "not_found": 1,
        "unchecked": 0, "hh_programmed": 160.0, "hh_finalized": 85.0,
        "pmp_count": 90, "not_programmed": 9, "from_prior_backlog": 0,
        "weeks_closed": 1, "weeks_total": 1, "all_weeks_closed": True,
    }
    data = {"weeks": [weekly], "monthly": monthly,
            "weekly_totals": {"hh_programmed": 160., "hh_finalized": 85.},
            "specialties": [], "unresolved": []}
    raw, filename = render_progress_fallback(data, 2026, 9, 7, [])
    assert filename == "informe_semanal_mtto_2026_09_7.pdf"
    assert b"INDICADORES PRINCIPALES" in raw
    assert b"CUMPLIMIENTO POR OT" in raw
    assert b"TEAM FOODS" in raw
    assert b"/Subtype /Image" in raw
    assert b"/Logo" in raw
    assert raw.count(b"/Type /Page ") >= 2
