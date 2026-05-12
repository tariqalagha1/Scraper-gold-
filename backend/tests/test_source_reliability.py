import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import create_app
from app.api.deps import get_db
from app.services.source_reliability_service import record_source_result, get_all_reliability_profiles, SOURCE_RELIABILITY

TEST_API_KEY = "test-global-api-key"

def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session
    return override_get_db

@pytest.fixture(autouse=True)
def reset_reliability():
    SOURCE_RELIABILITY.clear()
    yield

def test_record_source_result_creates_profile():
    record_source_result("internal", "success", 10, 0.9, 0.9, 1000.0, 1)
    profiles = get_all_reliability_profiles()
    assert "internal" in profiles
    assert profiles["internal"]["total_runs"] == 1
    assert profiles["internal"]["success_runs"] == 1
    assert profiles["internal"]["last_status"] == "success"

def test_success_rate_calculation():
    record_source_result("google_maps", "success", 10, 0.9, 0.9, 1000.0, 1)
    record_source_result("google_maps", "failed", 0, 0.0, 0.0, 1000.0, 0)
    
    profiles = get_all_reliability_profiles()
    prof = profiles["google_maps"]
    assert prof["total_runs"] == 2
    assert prof["success_runs"] == 1
    assert prof["failed_runs"] == 1
    
    # 0.5 success rate * 0.4 = 0.2, plus other metrics
    assert prof["reliability_score"] > 0

def test_empty_run_tracking():
    record_source_result("web", "success", 0, 0.0, 0.0, 1000.0, 0)
    profiles = get_all_reliability_profiles()
    prof = profiles["web"]
    assert prof["empty_runs"] == 1
    assert prof["success_runs"] == 0
    assert prof["last_status"] == "failed"

def test_reliability_score_clamped():
    record_source_result("perfect", "success", 10, 1.0, 1.0, 0.0, 0)
    prof = get_all_reliability_profiles()["perfect"]
    # success: 1.0 * 0.4 = 0.4
    # conf: 1.0 * 0.3 = 0.3
    # cov: 1.0 * 0.2 = 0.2
    # lat: 1.0 * 0.1 = 0.1
    # total = 1.0
    assert prof["reliability_score"] <= 1.0

@pytest.mark.asyncio
async def test_multi_source_response_includes_reliability(test_engine, monkeypatch):
    import app.services.multi_source_service as multi_module
    
    async def mock_run_source(source_name, request, trace_id):
        record_source_result(source_name, "success", 10, 1.0, 1.0, 1000.0, 0)
        return {"source_name": source_name, "result": {"final_data": [{"name": "A"}], "errors": []}}
        
    monkeypatch.setattr(multi_module, "_run_source", mock_run_source)
    
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    
    # Mock health endpoint
    import app.api.v1.scrape as scrape_api
    async def mock_health(*args, **kwargs):
        return {"database": "ok"}
    monkeypatch.setattr(scrape_api, "get_core_services_status", mock_health)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"query": "test", "location": "test", "limit": 10, "fields": ["name"], "sources": ["internal"]}
        res = await client.post("/api/v1/scrape/multi", headers={"X-API-Key": TEST_API_KEY}, json=payload)
    
    assert res.status_code == 200
    data = res.json()
    assert "source_reliability" in data["quality"]
    assert "internal" in data["quality"]["source_reliability"]

@pytest.mark.asyncio
async def test_reliability_endpoint_requires_api_key(test_engine):
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/scrape/sources/reliability")
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_reliability_endpoint_returns_profiles(test_engine):
    record_source_result("internal", "success", 10, 1.0, 1.0, 1000.0, 0)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/scrape/sources/reliability", headers={"X-API-Key": TEST_API_KEY})
    
    assert res.status_code == 200
    data = res.json()
    assert "sources" in data
    assert "internal" in data["sources"]
    assert data["sources"]["internal"]["success_runs"] == 1
