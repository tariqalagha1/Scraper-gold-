import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import create_app
from app.api.deps import get_db
from app.policy.policy_service import TENANT_POLICIES
from app.schemas.scrape import ScrapeRequest
from app.services.multi_source_service import execute_multi_source

TEST_API_KEY = "test-global-api-key"

def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session
    return override_get_db

@pytest.fixture(autouse=True)
def reset_policies():
    TENANT_POLICIES["default"] = {
        "allowed_sources": ["internal", "google_maps", "web"],
        "blocked_sources": [],
        "max_limit": 100,
        "max_execution_ms": 60000,
        "min_confidence": 0.4,
        "min_coverage": 0.5,
        "allow_fallback": True,
        "allow_force_sources": False,
        "allow_control_actions": True,
    }
    yield

@pytest.mark.asyncio
async def test_policy_loads_default_policy(test_engine, monkeypatch):
    import app.services.multi_source_service as multi_module
    async def mock_run_source(src, req, trace_id):
        return {"source_name": src, "result": {"final_data": [{"name": "A"}], "errors": []}}
    monkeypatch.setattr(multi_module, "_run_source", mock_run_source)

    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    
    import app.api.v1.scrape as scrape_api
    async def mock_health(*args, **kwargs):
        return {"database": "ok"}
    monkeypatch.setattr(scrape_api, "get_core_services_status", mock_health)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"query": "test", "location": "test", "limit": 10, "fields": ["name"], "sources": ["internal"]}
        res = await client.post("/api/v1/scrape/multi", headers={"X-API-Key": TEST_API_KEY}, json=payload)
    
    assert res.status_code == 200
    assert "policy" in res.json()["quality"]
    assert res.json()["quality"]["policy"]["tenant_id"] == "default"

@pytest.mark.asyncio
async def test_policy_filters_disallowed_sources(test_engine, monkeypatch):
    TENANT_POLICIES["default"]["blocked_sources"] = ["google_maps"]
    TENANT_POLICIES["default"]["allowed_sources"] = ["internal", "google_maps"]
    
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    
    import app.api.v1.scrape as scrape_api
    async def mock_health(*args, **kwargs):
        return {"database": "ok"}
    monkeypatch.setattr(scrape_api, "get_core_services_status", mock_health)
    
    import app.services.multi_source_service as multi_module
    async def mock_run_source(src, req, trace_id):
        return {"source_name": src, "result": {"final_data": [{"name": "A"}], "errors": []}}
    monkeypatch.setattr(multi_module, "_run_source", mock_run_source)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"query": "test", "location": "test", "limit": 10, "fields": ["name"], "sources": ["internal", "google_maps", "web"]}
        res = await client.post("/api/v1/scrape/multi", headers={"X-API-Key": TEST_API_KEY}, json=payload)
    
    assert res.status_code == 200
    quality = res.json()["quality"]
    assert "google_maps" in quality["policy"]["sources_filtered"]
    assert "web" in quality["policy"]["sources_filtered"]
    assert "internal" not in quality["policy"]["sources_filtered"]

@pytest.mark.asyncio
async def test_policy_rejects_when_no_allowed_sources(test_engine, monkeypatch):
    TENANT_POLICIES["default"]["allowed_sources"] = ["internal"]
    
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    
    import app.api.v1.scrape as scrape_api
    async def mock_health(*args, **kwargs):
        return {"database": "ok"}
    monkeypatch.setattr(scrape_api, "get_core_services_status", mock_health)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"query": "test", "location": "test", "limit": 10, "fields": ["name"], "sources": ["google_maps"]}
        res = await client.post("/api/v1/scrape/multi", headers={"X-API-Key": TEST_API_KEY}, json=payload)
    
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_policy_blocks_force_sources_when_not_allowed(test_engine):
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"query": "test", "location": "test", "limit": 10, "fields": ["name"], "sources": ["internal"], "force_sources": True}
        res = await client.post("/api/v1/scrape/multi", headers={"X-API-Key": TEST_API_KEY}, json=payload)
    
    assert res.status_code == 403
    assert "force_sources is not allowed" in res.json()["detail"]

@pytest.mark.asyncio
async def test_policy_caps_limit(test_engine, monkeypatch):
    TENANT_POLICIES["default"]["max_limit"] = 5
    
    import app.services.multi_source_service as multi_module
    async def mock_run_source(src, req, trace_id):
        return {"source_name": src, "result": {"final_data": [{"name": f"A{i}"} for i in range(10)], "errors": []}}
    monkeypatch.setattr(multi_module, "_run_source", mock_run_source)

    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    
    import app.api.v1.scrape as scrape_api
    async def mock_health(*args, **kwargs):
        return {"database": "ok"}
    monkeypatch.setattr(scrape_api, "get_core_services_status", mock_health)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"query": "test", "location": "test", "limit": 10, "fields": ["name"], "sources": ["internal"]}
        res = await client.post("/api/v1/scrape/multi", headers={"X-API-Key": TEST_API_KEY}, json=payload)
    
    assert res.status_code == 200
    assert res.json()["total"] == 5
    assert res.json()["quality"]["policy"]["limit_capped"] is True

@pytest.mark.asyncio
async def test_policy_marks_low_quality_result_partial(test_engine, monkeypatch):
    TENANT_POLICIES["default"]["min_coverage"] = 0.99
    
    import app.services.multi_source_service as multi_module
    async def mock_run_source(src, req, trace_id):
        return {"source_name": src, "result": {"final_data": [{"name": "A"}], "errors": []}} # misses phone, so coverage = 0.5
    monkeypatch.setattr(multi_module, "_run_source", mock_run_source)

    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    
    import app.api.v1.scrape as scrape_api
    async def mock_health(*args, **kwargs):
        return {"database": "ok"}
    monkeypatch.setattr(scrape_api, "get_core_services_status", mock_health)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"query": "test", "location": "test", "limit": 10, "fields": ["name", "phone"], "sources": ["internal"]}
        res = await client.post("/api/v1/scrape/multi", headers={"X-API-Key": TEST_API_KEY}, json=payload)
    
    assert res.status_code == 200
    assert res.json()["status"] == "partial"
    assert "Result below tenant quality policy threshold" in res.json()["errors"]

@pytest.mark.asyncio
async def test_policy_control_action_permission(test_engine):
    TENANT_POLICIES["default"]["allow_control_actions"] = False
    
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.post("/api/v1/control/test-trace/cancel", headers={"X-API-Key": TEST_API_KEY})
    
    assert res.status_code == 403
    assert "Control actions are disabled" in res.json()["detail"]

@pytest.mark.asyncio
async def test_policy_disables_fallback(test_engine, monkeypatch):
    TENANT_POLICIES["default"]["allow_fallback"] = False
    
    import app.services.multi_source_service as multi_module
    async def mock_run_source(src, req, trace_id):
        if src == "internal":
            return {"source_name": src, "result": {"final_data": [{"name": "A"}], "errors": []}}
        return {"source_name": src, "result": {"final_data": [], "errors": []}}
    monkeypatch.setattr(multi_module, "_run_source", mock_run_source)

    from app.services.source_reliability_service import record_source_result
    record_source_result("internal", "success", 10, 1.0, 1.0, 100.0, 0) # High
    record_source_result("web", "success", 10, 0.1, 0.1, 1000.0, 0) # Low

    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    
    import app.api.v1.scrape as scrape_api
    async def mock_health(*args, **kwargs):
        return {"database": "ok"}
    monkeypatch.setattr(scrape_api, "get_core_services_status", mock_health)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Request 10 but internal returns 1 (which triggers fallback logic), but allow_fallback is False
        payload = {"query": "test", "location": "test", "limit": 10, "fields": ["name"], "sources": ["internal", "web"]}
        res = await client.post("/api/v1/scrape/multi", headers={"X-API-Key": TEST_API_KEY}, json=payload)
    
    assert res.status_code == 200
    assert "low" not in res.json()["quality"]["tiers_executed"]
    assert res.json()["quality"]["fallback_used"] is False

@pytest.mark.asyncio
async def test_policy_events_emitted(test_engine, monkeypatch):
    TENANT_POLICIES["default"]["max_limit"] = 5
    
    from app.observability.event_emitter import EVENT_BUFFER
    EVENT_BUFFER.clear()
    
    import app.services.multi_source_service as multi_module
    async def mock_run_source(src, req, trace_id):
        return {"source_name": src, "result": {"final_data": [{"name": f"A"}], "errors": []}}
    monkeypatch.setattr(multi_module, "_run_source", mock_run_source)

    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    
    import app.api.v1.scrape as scrape_api
    async def mock_health(*args, **kwargs):
        return {"database": "ok"}
    monkeypatch.setattr(scrape_api, "get_core_services_status", mock_health)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"query": "test", "location": "test", "limit": 10, "fields": ["name"], "sources": ["internal"]}
        res = await client.post("/api/v1/scrape/multi", headers={"X-API-Key": TEST_API_KEY}, json=payload)
    
    events = [e["event_type"] for e in EVENT_BUFFER]
    assert "POLICY_APPLIED" in events
    assert "POLICY_LIMIT_CAPPED" in events
