from datetime import date
from pathlib import Path

from backend.services.v2_import_service import _order_source_key


SERVICE = Path("backend/services/v2_import_service.py").read_text(encoding="utf-8")


def test_v2_import_reconciles_without_broad_reset():
    assert "TRUNCATE TABLE" not in SERVICE
    for table in (
        "programacion.activo",
        "programacion.plan_trabajo",
        "programacion.planeacion",
        "programacion.orden_mantenimiento",
        "programacion.tecnico",
        "programacion.programacion_tecnico",
    ):
        assert table in SERVICE
    assert SERVICE.count("ON CONFLICT") >= 6


def test_order_identity_ignores_mutable_source_fields():
    base = {
        "numero_ot_raw": "OT-001",
        "activo_codigo": "A-1",
        "plan_clave_software": "PLAN-1",
        "cronograma_planeacion": "CRON-1",
        "titulo": "Título original",
        "responsable": "Persona A",
        "estado": "PENDIENTE",
        "tiempo_planeado_min": 60,
    }
    changed = {**base, "titulo": "Título corregido", "responsable": "Persona B", "estado": "FINALIZADO"}
    assert _order_source_key(date(2026, 9, 1), base, 1) == _order_source_key(date(2026, 9, 1), changed, 1)


def test_reconciliation_updates_source_fields_without_touching_complement_columns():
    assert "numero_personas_app=EXCLUDED" not in SERVICE
    assert "tiempo_parada_app_min=EXCLUDED" not in SERVICE
    assert "numero_personas=EXCLUDED.numero_personas" in SERVICE
    assert "tiempo_parada_min=EXCLUDED.tiempo_parada_min" in SERVICE


def test_historical_tables_are_not_import_targets():
    reset = SERVICE[SERVICE.find("with get_engine().begin()") : SERVICE.find("status=conn.execute")]
    assert "programacion_semanal_v2" not in reset
    assert "programacion_item_v2" not in reset
    assert "backlog_v2" not in reset
    assert "cierre_semanal_v2" not in reset
