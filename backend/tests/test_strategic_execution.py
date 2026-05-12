import pytest
from app.schemas.scrape import ScrapeRequest
from app.services.multi_source_service import execute_multi_source
from app.services.source_reliability_service import record_source_result, SOURCE_RELIABILITY

@pytest.fixture(autouse=True)
def reset_reliability():
    SOURCE_RELIABILITY.clear()
    yield

@pytest.mark.asyncio
async def test_high_tier_only_early_stop(monkeypatch):
    # internal -> High (1.0), google_maps -> Medium (0.5), web -> Low (0.1)
    record_source_result("internal", "success", 10, 1.0, 1.0, 100.0, 0)
    record_source_result("google_maps", "success", 10, 0.2, 0.2, 1000.0, 0)
    record_source_result("web", "failed", 0, 0.0, 0.0, 50000.0, 0)
    
    async def mock_run_pipeline(payload):
        return {"final_data": [{"name": f"Item {i}", "email": f"{i}@ex.com"} for i in range(10)], "errors": [], "quality_metrics": {"coverage": 1.0, "confidence": 1.0}}
        
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    request = ScrapeRequest(query="test", location="test", limit=10, fields=["name"], sources=["internal", "google_maps", "web"])
    res = await execute_multi_source(request)
    
    assert res["early_stopped"] is True
    assert "high" in res["tiers_executed"]
    assert "medium" not in res["tiers_executed"]
    assert "low" not in res["tiers_executed"]

@pytest.mark.asyncio
async def test_medium_tier_triggered(monkeypatch):
    record_source_result("internal", "success", 10, 1.0, 1.0, 100.0, 0)
    record_source_result("google_maps", "success", 10, 0.2, 0.2, 1000.0, 0)
    
    async def mock_run_pipeline(payload):
        if payload.get("source_type") == "internal":
            # Insufficient (only 5, need 8)
            return {"final_data": [{"name": f"A {i}"} for i in range(5)], "errors": [], "quality_metrics": {"coverage": 1.0}}
        if payload.get("source_type") == "google_maps":
            return {"final_data": [{"name": f"B {i}"} for i in range(5)], "errors": [], "quality_metrics": {"coverage": 1.0}}
        return {"final_data": [], "errors": []}
        
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    request = ScrapeRequest(query="test", location="test", limit=10, fields=["name"], sources=["internal", "google_maps"])
    res = await execute_multi_source(request)
    
    assert "high" in res["tiers_executed"]
    assert "medium" in res["tiers_executed"]
    assert len(res["final_data"]) == 10

@pytest.mark.asyncio
async def test_low_tier_fallback(monkeypatch):
    record_source_result("internal", "success", 10, 1.0, 1.0, 100.0, 0)
    record_source_result("google_maps", "success", 10, 0.2, 0.2, 1000.0, 0)
    record_source_result("web", "failed", 0, 0.0, 0.0, 50000.0, 0)
    
    async def mock_run_pipeline(payload):
        if payload.get("source_type") == "internal":
            return {"final_data": [{"name": "A"}], "errors": [], "quality_metrics": {"coverage": 1.0}}
        if payload.get("source_type") == "google_maps":
            return {"final_data": [{"name": "B"}], "errors": [], "quality_metrics": {"coverage": 1.0}}
        if payload.get("source_type") == "web":
            return {"final_data": [{"name": "C"}], "errors": [], "quality_metrics": {"coverage": 1.0}}
        return {"final_data": [], "errors": []}
        
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    # 2 records out of 10 limit is < 50%, so fallback to low tier should trigger
    request = ScrapeRequest(query="test", location="test", limit=10, fields=["name"], sources=["internal", "google_maps", "web"], force_sources=True)
    res = await execute_multi_source(request)
    
    assert "low" in res["tiers_executed"]
    assert res["fallback_used"] is True

@pytest.mark.asyncio
async def test_retry_logic(monkeypatch):
    record_source_result("internal", "success", 10, 1.0, 1.0, 100.0, 0)
    
    call_counts = {"internal": 0}
    
    async def mock_run_pipeline(payload):
        call_counts["internal"] += 1
        if call_counts["internal"] == 1:
            return {"status": "failed", "final_data": [], "errors": ["timeout"]}
        else:
            return {"status": "success", "final_data": [{"name": "A"}], "errors": []}
            
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    request = ScrapeRequest(query="test", location="test", limit=10, fields=["name"], sources=["internal"])
    res = await execute_multi_source(request)
    
    assert "internal" in res["retries_triggered"]
    assert call_counts["internal"] == 2
    assert len(res["final_data"]) == 1

@pytest.mark.asyncio
async def test_dynamic_limit(monkeypatch):
    record_source_result("internal", "success", 10, 1.0, 1.0, 100.0, 0)
    record_source_result("google_maps", "success", 10, 0.2, 0.2, 1000.0, 0)
    
    captured_limits = {}
    
    async def mock_run_pipeline(payload):
        src = payload.get("source_type")
        captured_limits[src] = payload.get("limit")
        if src == "internal":
            return {"final_data": [{"name": f"A{i}"} for i in range(5)], "errors": []}
        if src == "google_maps":
            return {"final_data": [{"name": f"B{i}"} for i in range(5)], "errors": []}
        return {"final_data": [], "errors": []}
        
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    request = ScrapeRequest(query="test", location="test", limit=10, fields=["name"], sources=["internal", "google_maps"])
    res = await execute_multi_source(request)
    
    assert captured_limits["internal"] == 10
    assert captured_limits["google_maps"] == 5 # 10 - 5 = 5
