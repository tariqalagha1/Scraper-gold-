from importlib import import_module


def test_app_main_imports_successfully():
    module = import_module("app.main")

    assert module.app is not None


def test_required_routers_are_registered():
    api_v1 = import_module("app.api.v1")
    paths = {route.path for route in api_v1.v1_router.routes}

    assert "/api/v1/jobs" in paths
    assert "/api/v1/exports" in paths
    assert "/api/v1/runs" in paths
    assert "/api/v1/assistant/request-refinement" in paths
    assert "/api/v1/scrape" in paths


def test_required_route_modules_import_successfully():
    jobs_module = import_module("app.api.v1.jobs")
    exports_module = import_module("app.api.v1.exports")
    runs_module = import_module("app.api.v1.runs")
    assistant_module = import_module("app.api.v1.assistant")
    scrape_module = import_module("app.api.v1.scrape")

    assert jobs_module.router is not None
    assert exports_module.router is not None
    assert runs_module.router is not None
    assert assistant_module.router is not None
    assert scrape_module.router is not None
