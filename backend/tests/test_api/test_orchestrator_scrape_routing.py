from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.orchestrator.smart_orchestrator import SmartOrchestrator
from app.orchestrator import smart_orchestrator as smart_module
from app.api.v1.scrape import run_pipeline

pytestmark = pytest.mark.asyncio


def _task_request() -> dict[str, object]:
    return {
        "task_type": "scrape",
        "task_id": "brainit-task-99",
        "input_payload": {
            "query": "hospitals",
            "location": "Saudi Arabia",
            "limit": 10,
            "fields": ["name", "contact", "email"],
        },
    }

async def test_smart_orchestrator_routes_scrape_task_to_scraper_agent(monkeypatch):
    executor_called = {"value": False}
    captured_input = {}

    async def fake_executor(input_data):
        executor_called["value"] = True
        return {"status": "failed"}

    class FakeScraperAgent:
        async def safe_execute(self, input_data):
            captured_input.update(input_data)
            return {
                "status": "success",
                "data": {
                    "agent": "scraper_agent",
                    "status": "completed",
                    "summary": {"total": 3, "coverage": 0.81, "confidence": 0.77},
                    "output_payload": {
                        "data": [{"name": "A"}, {"name": "B"}, {"name": "C"}],
                        "sources": [{"name": "source-1", "count": 3}],
                        "quality": {
                            "duplicates_removed": 1,
                            "coverage": 0.81,
                            "confidence": 0.77,
                            "missing_fields": {"email": 1},
                            "normalized_fields": 3,
                        },
                        "errors": [],
                        "request_id": "brainit-task-99",
                        "execution_time": 1.1,
                    },
                    "insights": {
                        "summary": "Found 3 records across 1 source.",
                        "key_findings": [],
                        "data_quality_note": "Result quality is high.",
                        "recommended_next_step": "Proceed to export results.",
                    },
                    "execution_steps": [
                        {
                            "step": 1,
                            "agent": "scraper_agent",
                            "service": "smart-scraper",
                            "input_summary": {"query": "hospitals"},
                            "output_summary": {"total": 3, "confidence": 0.77},
                            "status": "completed",
                        }
                    ],
                    "scraper_request_id": "brainit-task-99",
                    "scraper_execution_time": 1.1,
                    "scraper_confidence": 0.77,
                },
                "error": None,
                "metadata": {"agent": "scraper_agent", "timestamp": "2026-01-01T00:00:00+00:00"},
            }

    monkeypatch.setattr(smart_module, "_create_scraper_agent", lambda: FakeScraperAgent())

    result = await SmartOrchestrator(executor=fake_executor).run(_task_request())

    assert executor_called["value"] is False
    assert captured_input["task_type"] == "scrape"
    assert result["task_type"] == "scrape"
    assert result["agent"] == "scraper_agent"
    assert result["status"] == "completed"

# Test 1 & 2: Contract scrape uses task mode only and input is not mutated
async def test_contract_scrape_uses_task_mode_and_preserves_input(monkeypatch):
    executor_called = {"value": False}
    captured_input = {}
    
    async def fake_executor(input_data):
        executor_called["value"] = True
        return {"status": "failed"}

    class FakeScraperAgent:
        async def safe_execute(self, input_data):
            captured_input.update(input_data)
            return {
                "status": "success",
                "data": {
                    "agent": "scraper_agent",
                    "status": "completed",
                    "summary": {"total": 1, "coverage": 1.0, "confidence": 1.0},
                    "output_payload": {
                        "data": [],
                        "sources": [],
                        "quality": {"duplicates_removed": 0, "coverage": 1.0, "confidence": 1.0, "missing_fields": {}, "normalized_fields": 0},
                        "errors": [],
                        "request_id": "test-id",
                        "execution_time": 1.0
                    },
                    "insights": {"summary": "x", "key_findings": [], "data_quality_note": "x", "recommended_next_step": "x"},
                    "execution_steps": [],
                    "metadata": {"service": "smart-scraper", "task_type": "scrape"},
                    "errors": []
                }
            }

    monkeypatch.setattr(smart_module, "_create_scraper_agent", lambda: FakeScraperAgent())
    monkeypatch.setattr(smart_module, "decision_layer", AsyncMock())
    
    req = {
        "task_type": "scrape",
        "task_id": "req-123",
        "input_payload": {
            "query": "coffee shops",
            "location": "riyadh",
            "limit": 5,
            "fields": ["name", "phone"]
        }
    }
    
    orchestrator = SmartOrchestrator(executor=fake_executor)
    await orchestrator.run(req)
    
    assert executor_called["value"] is False, "pipeline should not be called"
    assert smart_module.decision_layer.called is False, "decision layer should not be called"
    
    payload = captured_input.get("input_payload", {})
    assert payload.get("query") == "coffee shops"
    assert payload.get("location") == "riyadh"
    assert payload.get("limit") == 5
    assert payload.get("fields") == ["name", "phone"]

# Test 3: Optional agents not called
async def test_optional_agents_not_called_in_contract_mode(monkeypatch):
    class FakeScraperAgent:
        async def safe_execute(self, input_data):
            return {"status": "success", "data": {"agent": "scraper_agent", "status": "completed", "summary": {"total": 1, "coverage": 1.0, "confidence": 1.0}, "output_payload": {"data": [], "sources": [], "quality": {"duplicates_removed": 0, "coverage": 1.0, "confidence": 1.0, "missing_fields": {}, "normalized_fields": 0}, "errors": [], "request_id": "test-id", "execution_time": 1.0}, "insights": {"summary": "x", "key_findings": [], "data_quality_note": "x", "recommended_next_step": "x"}, "execution_steps": [], "metadata": {"service": "smart-scraper", "task_type": "scrape"}, "errors": []}}
            
    monkeypatch.setattr(smart_module, "_create_scraper_agent", lambda: FakeScraperAgent())
    
    mock_processing = AsyncMock()
    mock_vector = AsyncMock()
    mock_analysis = AsyncMock()
    mock_export = AsyncMock()
    
    monkeypatch.setattr("app.orchestrator.nodes.processing_node", mock_processing)
    monkeypatch.setattr("app.orchestrator.nodes.vector_node", mock_vector)
    monkeypatch.setattr("app.orchestrator.nodes.analysis_node", mock_analysis)
    monkeypatch.setattr("app.orchestrator.nodes.export_node", mock_export)
    
    orchestrator = SmartOrchestrator()
    await orchestrator.run(_task_request())
    
    assert mock_processing.called is False
    assert mock_vector.called is False
    assert mock_analysis.called is False
    assert mock_export.called is False

# Test 4: Clean response contract preserved
async def test_clean_response_contract_preserved(monkeypatch):
    class FakeScraperAgent:
        async def safe_execute(self, input_data):
            return {"status": "success", "data": {"agent": "scraper_agent", "status": "completed", "summary": {"total": 1, "coverage": 1.0, "confidence": 1.0}, "output_payload": {"data": [{"name": "A"}], "sources": [], "quality": {"duplicates_removed": 0, "coverage": 1.0, "confidence": 1.0, "missing_fields": {}, "normalized_fields": 0}, "errors": [], "request_id": "test-id", "execution_time": 1.0}, "insights": {"summary": "x", "key_findings": [], "data_quality_note": "x", "recommended_next_step": "x"}, "execution_steps": [], "metadata": {"service": "smart-scraper", "task_type": "scrape"}, "errors": []}}
            
    monkeypatch.setattr(smart_module, "_create_scraper_agent", lambda: FakeScraperAgent())
    
    result = await run_pipeline({
        "query": "coffee shops",
        "location": "riyadh",
        "limit": 5,
        "fields": ["name", "phone"]
    })
    
    assert "status" in result
    assert "final_data" in result
    assert "sources" in result
    assert "errors" in result
    assert "quality_metrics" in result
    assert "WorkflowState" not in result
    assert "raw_data" not in result
    assert "processed_data" not in result

# Test 5: Full pipeline still works for non-contract jobs
async def test_full_pipeline_works_for_non_contract_jobs(monkeypatch):
    executor_called = {"value": False}
    
    async def fake_executor(input_data):
        executor_called["value"] = True
        return {"status": "completed", "processed_data": {"items": []}, "trace": {}}
        
    monkeypatch.setattr(smart_module, "decision_layer", AsyncMock(return_value={"decision_id": "1", "page_type": "list"}))
    monkeypatch.setattr(smart_module, "get_domain_memory", lambda d, p: None)
    monkeypatch.setattr(smart_module, "save_domain_memory", lambda d, p, v: None)
    
    orchestrator = SmartOrchestrator(executor=fake_executor)
    
    req = {
        "url": "https://example.com",
        "job_id": "job-1",
        "strategy": {}
    }
    
    res = await orchestrator.run(req)
    
    assert executor_called["value"] is True
    assert smart_module.decision_layer.called is True
    assert "result" in res
    assert "execution" in res
