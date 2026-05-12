from __future__ import annotations

import pytest

from app.agents.scraper_agent import ScraperAgent
from app.schemas.scraper import SmartScraperResponse
from app.services.scraper_client import ScraperClientError

pytestmark = pytest.mark.asyncio


def _task_payload() -> dict[str, object]:
    return {
        "task_type": "scrape",
        "task_id": "brainit-task-77",
        "input_payload": {
            "query": "hospitals",
            "location": "Saudi Arabia",
            "limit": 50,
            "fields": ["name", "contact", "email"],
        },
    }


def _scraper_response(status: str = "completed") -> SmartScraperResponse:
    return SmartScraperResponse.model_validate(
        {
            "request_id": "brainit-task-77",
            "status": status,
            "execution_time": 1.2,
            "total": 2 if status != "failed" else 0,
            "data": [{"name": "A"}, {"name": "B"}] if status != "failed" else [],
            "sources": [{"name": "source-1", "count": 2 if status != "failed" else 0}],
            "errors": [] if status == "completed" else ["partial source timeout"] if status == "partial" else ["failed"],
            "quality": {
                "duplicates_removed": 1,
                "coverage": 0.82 if status != "failed" else 0.0,
                "confidence": 0.79 if status != "failed" else 0.0,
                "missing_fields": {"email": 1} if status != "failed" else {},
                "normalized_fields": 3,
            },
        }
    )


async def test_scraper_agent_successful_call_path(monkeypatch):
    agent = ScraperAgent()

    async def fake_scrape(payload):
        response = _scraper_response("completed")
        return response.model_copy(update={"total": 99})

    monkeypatch.setattr(agent.scraper_client, "scrape", fake_scrape)
    result = await agent.safe_execute(_task_payload())

    assert result["status"] == "success"
    assert result["data"]["agent"] == "scraper_agent"
    assert result["data"]["status"] == "completed"
    assert result["data"]["summary"]["total"] == 2
    assert result["data"]["summary"]["total"] == len(result["data"]["output_payload"]["data"])
    assert result["data"]["output_payload"]["request_id"] == "brainit-task-77"
    assert result["data"]["metadata"]["service"] == "smart-scraper"
    assert result["data"]["metadata"]["task_type"] == "scrape"


async def test_scraper_agent_handles_partial_response(monkeypatch):
    agent = ScraperAgent()

    async def fake_scrape(payload):
        return _scraper_response("partial")

    monkeypatch.setattr(agent.scraper_client, "scrape", fake_scrape)
    result = await agent.safe_execute(_task_payload())

    assert result["status"] == "success"
    assert result["data"]["status"] == "partial"
    assert result["data"]["summary"]["confidence"] == 0.79


async def test_scraper_agent_handles_failed_response(monkeypatch):
    agent = ScraperAgent()

    async def fake_scrape(payload):
        return _scraper_response("failed")

    monkeypatch.setattr(agent.scraper_client, "scrape", fake_scrape)
    result = await agent.safe_execute(_task_payload())

    assert result["status"] == "fail"
    assert result["data"]["status"] == "failed"
    assert result["error"] == "Smart Scraper returned failed status."


@pytest.mark.parametrize(
    ("status_code", "message"),
    [
        (401, "missing API key"),
        (403, "invalid API key"),
        (422, "payload validation failed"),
        (503, "service unavailable"),
    ],
)
async def test_scraper_agent_maps_client_errors(monkeypatch, status_code: int, message: str):
    agent = ScraperAgent()

    async def fake_scrape(payload):
        raise ScraperClientError(
            message=message,
            code="scraper_http_error",
            status_code=status_code,
        )

    monkeypatch.setattr(agent.scraper_client, "scrape", fake_scrape)
    result = await agent.safe_execute(_task_payload())

    assert result["status"] == "fail"
    assert result["data"]["status"] == "failed"
    assert result["data"]["execution_steps"][0]["status"] == "failed"
    assert result["data"]["execution_steps"][0]["output_summary"]["http_status"] == status_code


async def test_scraper_agent_records_execution_steps(monkeypatch):
    agent = ScraperAgent()

    async def fake_scrape(payload):
        return _scraper_response("completed")

    monkeypatch.setattr(agent.scraper_client, "scrape", fake_scrape)
    result = await agent.safe_execute(_task_payload())

    steps = result["data"]["execution_steps"]
    assert len(steps) == 1
    assert steps[0]["step"] == 1
    assert steps[0]["agent"] == "scraper_agent"
    assert steps[0]["service"] == "smart-scraper"
    assert steps[0]["status"] == "completed"


async def test_scraper_agent_includes_insights_block(monkeypatch):
    agent = ScraperAgent()

    async def fake_scrape(payload):
        return _scraper_response("completed")

    monkeypatch.setattr(agent.scraper_client, "scrape", fake_scrape)
    result = await agent.safe_execute(_task_payload())

    insights = result["data"]["insights"]
    assert insights["summary"]
    assert isinstance(insights["key_findings"], list)
    assert 3 <= len(insights["key_findings"]) <= 5
    assert insights["data_quality_note"]
    assert insights["recommended_next_step"]


async def test_scraper_agent_findings_are_deterministic(monkeypatch):
    agent = ScraperAgent()

    async def fake_scrape(payload):
        return _scraper_response("completed")

    monkeypatch.setattr(agent.scraper_client, "scrape", fake_scrape)
    first = await agent.safe_execute(_task_payload())
    second = await agent.safe_execute(_task_payload())

    assert first["data"]["insights"]["summary"] == second["data"]["insights"]["summary"]
    assert first["data"]["insights"]["key_findings"] == second["data"]["insights"]["key_findings"]
    assert first["data"]["insights"]["recommended_next_step"] == second["data"]["insights"]["recommended_next_step"]


async def test_scraper_agent_quality_note_changes_with_quality_level(monkeypatch):
    agent = ScraperAgent()

    high_quality = SmartScraperResponse.model_validate(
        {
            "request_id": "hq",
            "status": "completed",
            "execution_time": 0.8,
            "total": 2,
            "data": [{"name": "A"}, {"name": "B"}],
            "sources": [{"name": "source-1", "count": 2}],
            "errors": [],
            "quality": {
                "duplicates_removed": 0,
                "coverage": 0.9,
                "confidence": 0.9,
                "missing_fields": {"name": 0, "email": 0},
                "normalized_fields": 2,
            },
        }
    )
    low_quality = SmartScraperResponse.model_validate(
        {
            "request_id": "lq",
            "status": "partial",
            "execution_time": 0.8,
            "total": 2,
            "data": [{"name": "A"}, {"name": "B"}],
            "sources": [{"name": "source-1", "count": 2}],
            "errors": ["timeout"],
            "quality": {
                "duplicates_removed": 0,
                "coverage": 0.4,
                "confidence": 0.4,
                "missing_fields": {"name": 0, "email": 2},
                "normalized_fields": 2,
            },
        }
    )

    async def fake_scrape_high(payload):
        return high_quality

    async def fake_scrape_low(payload):
        return low_quality

    monkeypatch.setattr(agent.scraper_client, "scrape", fake_scrape_high)
    high_result = await agent.safe_execute(_task_payload())
    monkeypatch.setattr(agent.scraper_client, "scrape", fake_scrape_low)
    low_result = await agent.safe_execute(_task_payload())

    assert "high" in high_result["data"]["insights"]["data_quality_note"].lower()
    assert "limited" in low_result["data"]["insights"]["data_quality_note"].lower()


async def test_scraper_agent_normalizes_invalid_pagination_type():
    agent = ScraperAgent()

    assert agent._resolve_pagination_type("none") == "auto"
    assert agent._resolve_pagination_type("load-more") == "load_more"
    assert agent._resolve_pagination_type("infinite_scroll") == "scroll"


async def test_scraper_agent_runtime_config_uses_normalized_pagination_type_from_strategy():
    agent = ScraperAgent()

    runtime = agent._build_runtime_config(
        config={},
        strategy={"pagination_type": "loadmore"},
    )

    assert runtime["pagination_type"] == "load_more"


async def test_scraper_agent_resolves_linked_page_worker_count_bounds():
    agent = ScraperAgent()

    assert agent._resolve_linked_page_worker_count(
        config={"linked_page_workers": 99},
        strategy={},
        detail_url_count=3,
    ) == 3
    assert agent._resolve_linked_page_worker_count(
        config={"linked_page_workers": "0"},
        strategy={},
        detail_url_count=8,
    ) == 1
    assert agent._resolve_linked_page_worker_count(
        config={},
        strategy={},
        detail_url_count=7,
    ) == 4


async def test_scraper_agent_detail_page_limit_uses_linked_page_limit_fallback():
    agent = ScraperAgent()

    assert agent._resolve_detail_page_limit(
        config={"linked_page_limit": 6},
        strategy={},
        max_pages=10,
    ) == 6
