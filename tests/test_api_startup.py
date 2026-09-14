def test_fastapi_app_imports():
    from api.index import app
    assert app is not None
    paths={route.path for route in app.routes}
    assert "/api/health" in paths
    assert "/api/capacity" in paths
    assert "/api/programming/version/{version_id}/export.xlsx" in paths
    assert "/api/programming/version/{version_id}/export.pdf" in paths
    assert "/api/definitions/pending" in paths
    assert "/api/definitions/plans/{plan_id}" in paths
    assert "/api/v2/programming/week" in paths
    assert "/api/v2/backlog" in paths
    assert "/api/v2/programming/{programming_id}/closure" in paths
    assert "/api/v2/programming/{programming_id}/close-file" in paths
