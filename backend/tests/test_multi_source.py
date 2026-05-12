import pytest
from app.schemas.scrape import ScrapeRequest
from app.services.multi_source_service import execute_multi_source

@pytest.mark.asyncio
async def test_multi_source_execution(monkeypatch):
    async def mock_run_pipeline(payload):
        if payload.get("source_type") == "internal":
            return {"final_data": [{"name": "A", "email": "a@example.com", "source": "internal"}], "errors": []}
        elif payload.get("source_type") == "google_maps":
            return {"final_data": [{"name": "B", "email": "b@example.com", "source": "google_maps"}], "errors": []}
        return {"final_data": [], "errors": []}
    
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    request = ScrapeRequest(query="test", location="test", limit=10, fields=["name"], sources=["internal", "google_maps"])
    res = await execute_multi_source(request)
    
    assert len(res["final_data"]) == 2
    assert "internal" in res["sources_used"]
    assert "google_maps" in res["sources_used"]

@pytest.mark.asyncio
async def test_cross_source_deduplication(monkeypatch):
    async def mock_run_pipeline(payload):
        if payload.get("source_type") == "internal":
            return {"final_data": [{"name": "A", "email": "a@example.com", "source": "internal"}], "errors": []}
        elif payload.get("source_type") == "google_maps":
            return {"final_data": [{"name": "A", "email": "a@example.com", "source": "google_maps", "phone": "123"}], "errors": []}
        return {"final_data": [], "errors": []}
    
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    request = ScrapeRequest(query="test", location="test", limit=10, fields=["name"], sources=["internal", "google_maps"])
    res = await execute_multi_source(request)
    
    assert len(res["final_data"]) == 1
    assert res["cross_source_duplicates_removed"] == 1
    assert res["final_data"][0]["phone"] == "123" # merged

@pytest.mark.asyncio
async def test_ranking(monkeypatch):
    async def mock_run_pipeline(payload):
        if payload.get("source_type") == "internal":
            return {"final_data": [{"name": "B", "email": "b@example.com"}], "errors": []}
        elif payload.get("source_type") == "google_maps":
            return {"final_data": [{"name": "A", "email": "a@example.com", "phone": "123", "address": "123 St"}], "errors": []}
        return {"final_data": [], "errors": []}
    
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    request = ScrapeRequest(query="test", location="test", limit=10, fields=["name", "email", "phone", "address"], sources=["internal", "google_maps"])
    res = await execute_multi_source(request)
    
    # Google maps record (A) should have higher score due to more completeness/coverage
    assert res["final_data"][0]["name"] == "A"
    assert res["final_data"][1]["name"] == "B"

@pytest.mark.asyncio
async def test_limit_enforcement(monkeypatch):
    async def mock_run_pipeline(payload):
        return {"final_data": [{"name": str(i), "email": f"{i}@ex.com"} for i in range(10)], "errors": []}
        
    monkeypatch.setattr("app.services.multi_source_service.run_pipeline", mock_run_pipeline)
    
    request = ScrapeRequest(query="test", location="test", limit=5, fields=["name"], sources=["internal"])
    res = await execute_multi_source(request)
    
    assert len(res["final_data"]) == 5
