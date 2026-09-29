from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_app_specialty_has_priority_over_software_specialty():
    source = (
        ROOT
        / "supabase/migrations/20260929142000_technician_app_specialty_override_priority.sql"
    ).read_text()
    assert "COALESCE(especialidad_app, especialidad)" in source


def test_specialty_override_can_update_existing_technician():
    source = (ROOT / "backend/services/v2_query_service.py").read_text()
    assert "SET especialidad_app=:specialty" in source
    assert "CASE WHEN especialidad IS NULL THEN :specialty" not in source
    assert "refresh_open_program_capacities(conn)" in source


def test_technician_matrix_exposes_inline_specialty_editor():
    source = (ROOT / "frontend/src/components/TechnicianSchedule.jsx").read_text()
    assert "tech-specialty-editor" in source
    assert "Especialidad de" in source
    assert "Restaurar especialidad del software" in source


def test_capacity_copy_explains_first_twenty_percent_as_operational_time():
    technician = (ROOT / "frontend/src/components/TechnicianSchedule.jsx").read_text()
    weekly = (ROOT / "frontend/src/components/WeeklyProgramming.jsx").read_text()
    assert "Alistamiento / tiempo no programable" in technician
    assert "Alistamiento / tiempo no programable" in weekly
    assert "80% preventivo / 20% correctivo-reserva" in weekly
