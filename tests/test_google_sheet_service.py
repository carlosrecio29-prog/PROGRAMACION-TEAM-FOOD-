from backend.services.google_sheet_service import _resolve_state


def test_resolve_finalized_order():
    assert _resolve_state(["FINALIZADA"]) == ("FINALIZADA", False)


def test_pending_wins_when_duplicate_rows_disagree():
    assert _resolve_state(["FINALIZADA", "PENDIENTE"]) == ("PENDIENTE", True)


def test_cancelled_only_is_not_found():
    assert _resolve_state(["ANULADA"]) == ("NO ENCONTRADA", False)


def test_unknown_single_state_is_preserved_for_review():
    assert _resolve_state(["EN PROCESO"]) == ("EN PROCESO", False)
