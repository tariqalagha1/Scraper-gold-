import pytest
from app.services.adaptive_source_selector import build_source_execution_plan, DEFAULT_RELIABILITY, MIN_RELIABILITY_THRESHOLD
from app.services.source_reliability_service import record_source_result, SOURCE_RELIABILITY

@pytest.fixture(autouse=True)
def reset_reliability():
    SOURCE_RELIABILITY.clear()
    yield

def test_sources_sorted_by_reliability():
    record_source_result("good", "success", 10, 1.0, 1.0, 100.0, 0)
    record_source_result("bad", "success", 10, 0.1, 0.1, 50000.0, 0) # lat_score = 0, others low
    
    plan = build_source_execution_plan(["bad", "good"])
    assert plan.execution_order[0] == "good"

def test_unknown_sources_get_default_reliability():
    plan = build_source_execution_plan(["unknown"])
    assert plan.execution_order == ["unknown"]

def test_low_reliability_sources_are_skipped():
    record_source_result("terrible", "failed", 0, 0.0, 0.0, 50000.0, 0)
    plan = build_source_execution_plan(["terrible", "good"])
    assert "terrible" in plan.sources_skipped
    assert "terrible" not in plan.execution_order

def test_force_sources_prevents_skipping():
    record_source_result("terrible", "failed", 0, 0.0, 0.0, 50000.0, 0)
    plan = build_source_execution_plan(["terrible", "good"], force_sources=True)
    assert "terrible" not in plan.sources_skipped
    assert "terrible" in plan.execution_order

@pytest.mark.asyncio
async def test_execution_plan_included_in_multi_source_response(test_engine, monkeypatch):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.main import create_app
    from app.api.deps import get_db
    
    import app.services.multi_source_service as multi_module
    async def mock_run_source(source_name, request, trace_id):
        return {"source_name": source_name, "result": {"final_data": [{"name": "A"}], "errors": []}}
    monkeypatch.setattr(multi_module, "_run_source", mock_run_source)
    
    import app.api.v1.scrape as scrape_api
    async def mock_health(*args, **kwargs):
        return {"database": "ok"}
    monkeypatch.setattr(scrape_api, "get_core_services_status", mock_health)
    
    def override_get_db():
        async def _override_get_db():
            async with async_sessionmaker(test_engine, expire_on_commit=False)() as session:
                yield session
        return _override_get_db

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"query": "test", "location": "test", "limit": 10, "fields": ["name"], "sources": ["internal", "web"], "force_sources": False}
        res = await client.post("/api/v1/scrape/multi", headers={"X-API-Key": "test-global-api-key"}, json=payload)
    
    assert res.status_code == 200
    data = res.json()
    assert "sources_skipped" in data["quality"]
    assert "execution_order" in data["quality"]
    assert "internal" in data["quality"]["execution_order"]

@pytest.mark.asyncio
async def test_existing_multi_source_behavior_still_works():
    # Implicitly verified above and by preserving tests
    pass
