"""Guard against silently deleting valid TiempoParada=0 on Plan Trabajo reloads."""
from backend.services.v2_maintenance_import_service import PLAN_UPSERT_SQL


def test_blank_plan_import_preserves_previously_known_stop_time():
    statement = " ".join(PLAN_UPSERT_SQL.split()).lower()
    assert (
        "tiempo_parada_min=coalesce(excluded.tiempo_parada_min, "
        "plan_trabajo.tiempo_parada_min)"
    ) in statement
    assert "tiempo_parada_min=excluded.tiempo_parada_min," not in statement


def test_zero_still_a_valid_input():
    from backend.services.v2_advance_stops import classify_advance
    from datetime import date

    row = {
        "fila_origen": 2, "activo_codigo": "BA-TEST",
        "plan_clave_software": "44-INSPECCION",
        "numero_ot_raw": "", "especialidad": "MEC",
        "tiempo_planeado_min": 30,
    }
    plan = {
        "es_operacion": False,
        "grupo": "44",
        "plan_trabajo": "INSPECCION",
        "tiempo_parada_efectivo_min": 0,
        "numero_personas_efectivo": 1,
        "tiempo_ejecucion_min": 30,
    }
    result = classify_advance(
        [row], {"44-INSPECCION": plan}, {}, date(2026, 10, 1)
    )
    assert result["operando"] == 1
    assert result["sin_definir"] == 0
    assert result["filas"][0]["tiempo_parada_min"] == 0
