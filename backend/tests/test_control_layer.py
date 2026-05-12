import pytest
import asyncio
from app.control.control_service import set_control, get_control, clear_control, CONTROL_STATE
from app.services.strategic_execution_service import execute_strategically
from app.schemas.scrape import ScrapeRequest

@pytest.fixture(autouse=True)
def reset_control():
    CONTROL_STATE.clear()
    yield
    CONTROL_STATE.clear()

def _mock_coverage(records, fields):
    return 1.0
    
def _mock_merge(existing, new):
    return existing + new, 0, [n.get("_source", "unknown") for n in new]

@pytest.mark.asyncio
async def test_cancel_execution():
    async def mock_run_source(src, req, trace_id):
        return {"source_name": src, "result": {"final_data": [{"name": "A"}], "errors": []}}
        
    trace_id = "test-cancel"
    set_control(trace_id, "cancel", True)
    
    req = ScrapeRequest(query="test", location="test", limit=10, fields=["name"])
    res = await execute_strategically(
        req, ["internal"], mock_run_source, _mock_merge, _mock_coverage, trace_id
    )
    
    assert len(res["tiers_executed"]) == 0
    assert len(res["final_data"]) == 0

@pytest.mark.asyncio
async def test_pause_and_resume():
    trace_id = "test-pause"
    
    async def mock_run_source(src, req, trace_id):
        return {"source_name": src, "result": {"final_data": [{"name": "A"}], "errors": []}}
        
    set_control(trace_id, "pause", True)
    
    # Run the execution in the background
    req = ScrapeRequest(query="test", location="test", limit=10, fields=["name"])
    task = asyncio.create_task(execute_strategically(
        req, ["internal"], mock_run_source, _mock_merge, _mock_coverage, trace_id
    ))
    
    # Assert it hasn't completed quickly
    done, pending = await asyncio.wait([task], timeout=0.1)
    assert len(pending) == 1
    
    # Resume
    set_control(trace_id, "pause", False)
    
    res = await task
    assert len(res["tiers_executed"]) > 0

@pytest.mark.asyncio
async def test_disable_source():
    trace_id = "test-disable"
    
    async def mock_run_source(src, req, trace_id):
        return {"source_name": src, "result": {"final_data": [{"name": "A"}], "errors": []}}
        
    set_control(trace_id, "disabled_sources", "google_maps")
    
    req = ScrapeRequest(query="test", location="test", limit=10, fields=["name"])
    res = await execute_strategically(
        req, ["google_maps"], mock_run_source, _mock_merge, _mock_coverage, trace_id
    )
    
    assert len(res["tiers_executed"]) == 0

@pytest.mark.asyncio
async def test_force_fallback():
    trace_id = "test-fallback"
    
    async def mock_run_source(src, req, trace_id):
        return {"source_name": src, "result": {"final_data": [{"name": "A"}], "errors": []}}
        
    set_control(trace_id, "force_fallback", True)
    
    req = ScrapeRequest(query="test", location="test", limit=10, fields=["name"])
    res = await execute_strategically(
        req, ["internal"], mock_run_source, _mock_merge, _mock_coverage, trace_id
    )
    
    # "internal" is typically mapped to HIGH, but since force_fallback is True, HIGH is skipped.
    assert len(res["tiers_executed"]) == 0

@pytest.mark.asyncio
async def test_override_tier():
    trace_id = "test-override"
    
    async def mock_run_source(src, req, trace_id):
        return {"source_name": src, "result": {"final_data": [{"name": "A"}], "errors": []}}
        
    set_control(trace_id, "override_tier", "low")
    
    req = ScrapeRequest(query="test", location="test", limit=10, fields=["name"])
    res = await execute_strategically(
        req, ["internal"], mock_run_source, _mock_merge, _mock_coverage, trace_id
    )
    
    assert len(res["tiers_executed"]) == 0 # internal is high tier, we only run low
