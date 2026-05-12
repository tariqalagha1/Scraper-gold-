import pytest
import asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import create_app
from app.api.deps import get_db
from app.observability.event_emitter import subscribe, unsubscribe, EVENT_BUFFER
from app.schemas.scrape import ScrapeRequest
from app.services.multi_source_service import execute_multi_source
from app.services.source_reliability_service import SOURCE_RELIABILITY

@pytest.fixture(autouse=True)
def reset_observability():
    EVENT_BUFFER.clear()
    SOURCE_RELIABILITY.clear()
    yield

def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session
    return override_get_db

@pytest.mark.asyncio
async def test_trace_id_propagation_and_event_emission(monkeypatch):
    async def mock_run_pipeline(payload):
        return {"final_data": [{"name": "A"}], "errors": [], "quality_metrics": {"coverage": 1.0}}
        
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    trace_id = "test-trace-123"
    request = ScrapeRequest(query="test", location="test", limit=10, fields=["name"], sources=["internal", "web"], force_sources=True)
    await execute_multi_source(request, trace_id)
    
    events = list(EVENT_BUFFER)
    assert len(events) > 0
    
    # Assert trace_id propagation
    assert all(e["trace_id"] == trace_id for e in events)
    
    event_types = {e["event_type"] for e in events}
    
    # Assert essential events emitted
    assert "SCRAPE_STARTED" in event_types
    assert "TIER_STARTED" in event_types
    assert "SOURCE_STARTED" in event_types
    assert "SOURCE_COMPLETED" in event_types
    
@pytest.mark.asyncio
async def test_source_failed_and_retry_event(monkeypatch):
    call_counts = {"internal": 0}
    
    async def mock_run_pipeline(payload):
        call_counts["internal"] += 1
        if call_counts["internal"] == 1:
            return {"status": "failed", "final_data": [], "errors": ["timeout"]}
        else:
            return {"status": "success", "final_data": [{"name": "A"}], "errors": []}
            
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    trace_id = "test-trace-456"
    request = ScrapeRequest(query="test", location="test", limit=10, fields=["name"], sources=["internal"])
    await execute_multi_source(request, trace_id)
    
    events = list(EVENT_BUFFER)
    event_types = {e["event_type"] for e in events}
    
    assert "SOURCE_FAILED" in event_types
    assert "RETRY_TRIGGERED" in event_types
    assert "SOURCE_COMPLETED" in event_types

@pytest.mark.asyncio
async def test_websocket_stream_and_latest(test_engine):
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(async_sessionmaker(test_engine, expire_on_commit=False))
    
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    from app.observability.event_emitter import emit
    emit("TEST_EVENT", {"foo": "bar"}, "test-ws-trace")
    
    res = client.get("/api/v1/events/latest", headers={"X-API-Key": "test-global-api-key"})
    assert res.status_code == 200
    assert "events" in res.json()
    assert res.json()["events"][-1]["event_type"] == "TEST_EVENT"
    
    # Simple websocket test 
    with client.websocket_connect(
        "/api/v1/events/stream",
        headers={"X-API-Key": "test-global-api-key"},
    ) as websocket:
        emit("WS_TEST_EVENT", {"ws": "data"}, "test-ws-trace-2")
        data = websocket.receive_json()
        assert data["event_type"] == "WS_TEST_EVENT"
        assert data["trace_id"] == "test-ws-trace-2"
