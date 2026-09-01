def test_fastapi_app_imports():
    from api.index import app
    assert app is not None
    paths={route.path for route in app.routes}
    assert "/api/health" in paths
    assert "/api/capacity" in paths
    assert "/api/programming/version/{version_id}/export.xlsx" in paths
    assert "/api/programming/version/{version_id}/export.pdf" in paths
