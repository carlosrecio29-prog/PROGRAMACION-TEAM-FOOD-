from backend.services.v2_programming_service import capacity_split


def test_two_stage_capacity_rule_from_200_hours():
    result = capacity_split(200)
    assert result == {
        "available": 200.0,
        "effective": 160.0,
        "preventive": 128.0,
        "corrective": 32.0,
        "initial_margin": 40.0,
    }


def test_capacity_rule_keeps_zero_safe():
    assert capacity_split(0) == {
        "available": 0.0,
        "effective": 0.0,
        "preventive": 0.0,
        "corrective": 0.0,
        "initial_margin": 0.0,
    }
