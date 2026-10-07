from backend.services.v2_query_service import _dashboard_progress_payload


def test_dashboard_progress_payload_calculates_program_advance():
    data = _dashboard_progress_payload({
        "total_orders": 984,
        "finalized_orders": 69,
        "pmp_orders": 723,
        "backlog_orders": 261,
        "total_workload_hh": 1542.35,
        "finalized_workload_hh": 321.25,
        "latest_tracking_at": "2026-10-06T19:43:11+00:00",
    })

    assert data["total_orders"] == 984
    assert data["finalized_orders"] == 69
    assert data["pending_orders"] == 915
    assert data["progress_pct"] == 7.0
    assert data["pmp_orders"] == 723
    assert data["backlog_orders"] == 261
    assert data["total_workload_hh"] == 1542.35
    assert data["finalized_workload_hh"] == 321.25
    assert data["progress_hh_pct"] == 20.8


def test_dashboard_progress_payload_never_exceeds_total():
    data = _dashboard_progress_payload({
        "total_orders": 10,
        "finalized_orders": 14,
        "pmp_orders": 8,
        "backlog_orders": 2,
        "latest_tracking_at": None,
    })

    assert data["finalized_orders"] == 10
    assert data["pending_orders"] == 0
    assert data["progress_pct"] == 100.0
