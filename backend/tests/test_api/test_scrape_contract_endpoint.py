import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db
from app.main import create_app

pytestmark = pytest.mark.asyncio
TEST_API_KEY = "test-global-api-key"

def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session
    return override_get_db

def _valid_payload() -> dict[str, object]:
    return {
        "query": "coffee shops",
        "location": "riyadh",
        "limit": 5,
        "fields": ["name", "phone"]
    }

async def test_scrape_endpoint_requires_api_key(test_engine):
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/scrape", json=_valid_payload())
    assert response.status_code == 401

async def test_scrape_endpoint_rejects_invalid_api_key(test_engine):
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/scrape", headers={"X-API-Key": "invalid"}, json=_valid_payload())
    assert response.status_code == 403

async def test_scrape_endpoint_fails_closed_when_health_unhealthy(test_engine, monkeypatch):
    import app.api.v1.scrape as scrape_api
    
    async def mock_health(*args, **kwargs):
        return {"database": "ok", "redis": "down"}
        
    monkeypatch.setattr(scrape_api, "get_core_services_status", mock_health)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/scrape", headers={"X-API-Key": TEST_API_KEY}, json=_valid_payload())
    
    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "down"

async def test_scrape_endpoint_rejects_invalid_schema(test_engine):
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    
    invalid_cases = [
        {"query": "", "location": "riyadh", "limit": 5, "fields": ["name"]}, # empty query
        {"location": "riyadh", "limit": 5, "fields": ["name"]}, # missing query
        {"query": "coffee shops", "location": "riyadh", "limit": 0, "fields": ["name"]}, # limit 0
        {"query": "coffee shops", "location": "riyadh", "limit": 101, "fields": ["name"]}, # limit > 100
        {"query": "coffee shops", "location": "riyadh", "limit": 5, "fields": "name"}, # fields not array
    ]
    
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for payload in invalid_cases:
            response = await client.post("/api/v1/scrape", headers={"X-API-Key": TEST_API_KEY}, json=payload)
            assert response.status_code == 422

async def test_scrape_endpoint_returns_clean_contract(test_engine):
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/scrape", headers={"X-API-Key": TEST_API_KEY}, json=_valid_payload())
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "total" in data
    assert "data" in data
    assert "sources" in data
    assert "errors" in data
    assert "quality" in data
    assert "duplicates_removed" in data["quality"]
    
    assert "WorkflowState" not in data
    assert "raw_data" not in data
    assert "processed_data" not in data
    assert "vector_data" not in data
    assert "analysis_data" not in data

async def test_scrape_endpoint_does_not_call_pipeline_or_optional_agents(test_engine, monkeypatch):
    import app.orchestrator.smart_orchestrator as smart_module
    from unittest.mock import AsyncMock
    
    mock_pipeline = AsyncMock()
    mock_decision = AsyncMock()
    
    monkeypatch.setattr("app.orchestrator.graph.run_pipeline", mock_pipeline)
    monkeypatch.setattr(smart_module, "decision_layer", mock_decision)
    
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/scrape", headers={"X-API-Key": TEST_API_KEY}, json=_valid_payload())
        
    assert response.status_code == 200
    assert mock_pipeline.called is False
    assert mock_decision.called is False

async def test_scrape_endpoint_preserves_input_payload(test_engine, monkeypatch):
    import app.orchestrator.smart_orchestrator as smart_module
    
    captured_payload = {}
    class FakeScraperAgent:
        async def safe_execute(self, input_data):
            captured_payload.update(input_data)
            return {"status": "success", "data": {"agent": "scraper_agent", "status": "completed", "summary": {"total": 1, "coverage": 1.0, "confidence": 1.0}, "output_payload": {"data": [], "sources": [], "quality": {"duplicates_removed": 0, "coverage": 1.0, "confidence": 1.0, "missing_fields": {}, "normalized_fields": 0}, "errors": [], "execution_time": 1.0}, "insights": {"summary": "x", "key_findings": [], "data_quality_note": "x", "recommended_next_step": "x"}, "execution_steps": [], "metadata": {"service": "smart-scraper", "task_type": "scrape"}, "errors": []}}
            
    monkeypatch.setattr(smart_module, "_create_scraper_agent", lambda: FakeScraperAgent())
    
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    payload = _valid_payload()
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/scrape", headers={"X-API-Key": TEST_API_KEY}, json=payload)
        
    assert response.status_code == 200
    input_payload = captured_payload.get("input_payload", {})
    assert input_payload.get("query") == payload["query"]
    assert input_payload.get("location") == payload["location"]
    assert input_payload.get("limit") == payload["limit"]
    assert input_payload.get("fields") == payload["fields"]
async def test_scrape_endpoint_fake_success_protection(test_engine, monkeypatch):
    import app.orchestrator.smart_orchestrator as smart_module
    
    class FakeScraperAgent:
        async def safe_execute(self, input_data):
            return {"status": "success", "data": {"agent": "scraper_agent", "status": "completed", "summary": {"total": 0, "coverage": 1.0, "confidence": 1.0}, "output_payload": {"data": [], "sources": [], "quality": {"duplicates_removed": 0, "coverage": 1.0, "confidence": 1.0, "missing_fields": {}, "normalized_fields": 0}, "errors": [], "execution_time": 1.0}, "insights": {"summary": "x", "key_findings": [], "data_quality_note": "x", "recommended_next_step": "x"}, "execution_steps": [], "metadata": {"service": "smart-scraper", "task_type": "scrape"}, "errors": []}}
            
    monkeypatch.setattr(smart_module, "_create_scraper_agent", lambda: FakeScraperAgent())
    
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/scrape", headers={"X-API-Key": TEST_API_KEY}, json=_valid_payload())
        
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert "No data returned" in response.json()["errors"]
