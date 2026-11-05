"""Informe gerencial mensual: métricas consistentes y exportación sin efectos laterales."""
import re

from backend.services.v2_monthly_executive_pdf import _data, render_monthly_executive_pdf


def fixture():
    return {
        "weeks": [
            {
                "programming_id": 38,
                "week_from": "2026-10-01",
                "week_to": "2026-10-07",
                "especialidad": "ELE",
                "estado": "CERRADA",
                "programmed": 146,
                "finalized": 70,
                "hh_programmed": 146.0,
            }
        ],
        "monthly": {
            "all_weeks_closed": True,
            "weeks_closed": 1,
            "weeks_total": 1,
            "pending": 49,
            "not_found": 0,
            "unchecked": 0,
            "not_programmed": 3,
            "from_prior_backlog": 18,
        },
        "monthly_progress_by_specialty": [
            {
                "especialidad": "ELE",
                "name": "Eléctrica",
                "total_ot": 479,
                "completed_ot": 410,
                "progress_ot_pct": 85.6,
                "scheduled_unique": 357,
                "scheduled_completed": 298,
                "scheduled_progress_ot_pct": 83.5,
                "scheduled_reprogrammed_assignments": 289,
                "unplanned_completed": 112,
                "total_hh": 653.56,
                "completed_hh": 382.77,
            }
        ],
        "unresolved": [
            {
                "numero_ot": "OT-TEST-26",
                "especialidad": "ELE",
                "activo": "BA-E1",
                "resultado": "PENDIENTE",
                "hh_estimada": 2.0,
            }
        ],
    }


def test_executive_kpis_are_unique_and_do_not_sum_weekly_reprogramming():
    m = _data(fixture())
    assert m["total"] == 479
    assert m["completed"] == 410
    assert m["planned_unique"] == 357
    assert m["planned_done"] == 298
    assert m["unplanned_done"] == 112
    assert m["repeated"] == 289
    assert m["general_pct"] == 85.6
    assert m["program_pct"] == 83.5
    assert m["hh_total"] == 653.56
    assert m["hh_done"] == 382.77


def test_seven_page_a4_executive_pdf_contains_real_data_and_branding():
    raw, filename = render_monthly_executive_pdf(fixture(), 2026, 10)
    assert filename == "informe_gerencial_cierre_mensual_2026_10.pdf"
    assert raw.startswith(b"%PDF-1.4")
    assert len(raw) > 20_000
    assert len(re.findall(rb"/Type\s*/Page\b", raw)) == 7
    for marker in (
        b"INFORME GERENCIAL", b"Resumen ejecutivo", b"Balance mensual",
        b"Desempe", b"Backlog y desviaciones", b"Conclusiones gerenciales",
        b"OT-TEST-26", b"479", b"410", b"357", b"298",
        b"85,6%", b"83,5%", b"H-H",
    ):
        assert marker in raw, marker
    assert b"/Subtype /Image" in raw  # Logos corporativos embebidos.


def test_partial_month_is_explicit_and_never_claims_formal_monthly_close():
    data = fixture()
    data["monthly"]["all_weeks_closed"] = False
    data["monthly"]["weeks_closed"] = 0
    raw, _ = render_monthly_executive_pdf(data, 2026, 10)
    assert b"INFORME PARCIAL" in raw
    assert b"PROGRAMACIONES ABIERTAS" in raw
    assert b"aprobaci" not in raw.lower()
