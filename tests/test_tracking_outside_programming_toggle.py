"""Regression: the visible outside-programming button must use the same Google Sheets audit."""
from pathlib import Path


def test_tracking_toggle_uses_audited_source_for_november():
    source = (Path(__file__).resolve().parents[1] /
              "frontend/src/components/WeeklyTracking.jsx").read_text(encoding="utf-8")

    # The button in the screenshot must never show the legacy zero for
    # an admin looking at November 2026 and later.
    assert 'const useAuditedOutside = accessRole === "admin"' in source
    assert 'const outsideToggleCount = useAuditedOutside' in source
    assert 'weeklyOutside ? number(weeklyOutside.total)' in source
    assert 'number(unplannedSummary.total)' in source  # historical fallback only
    assert '· {outsideToggleCount}' in source

    # The button expands a table immediately below the board heading,
    # not an unrelated panel after the scheduled-work table.
    assert "{showUnplanned && useAuditedOutside && (" in source
    assert "{showUnplanned && !useAuditedOutside && (" in source
    assert (source.index("{showUnplanned && useAuditedOutside && (")
            < source.index('className="weekly-tracking-filters"'))
    assert source.count("Finalizadas fuera de programación · Semana") == 1

    # Count, classification and row detail read the same audit API as closure/PDF.
    assert "getWeeklyOutsideFinalizations(year, month, specialty, week.from, week.to)" in source
    assert '<b>{number(weeklyOutside.total)}</b>' in source
    assert "weeklyOutside.programadas_otra_semana" not in source
    assert "weeklyOutside.fuera_del_mes" not in source
    assert "weeklyOutside.rows.slice(0,20)" in source
    assert "No se suman al" in source
