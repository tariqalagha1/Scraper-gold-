from __future__ import annotations

import json

import httpx
import pytest

from app.schemas.scraper import ScraperTaskInputPayload
from app.services.scraper_client import ScraperClient, ScraperClientError


def _payload() -> ScraperTaskInputPayload:
    return ScraperTaskInputPayload(
        query="hospitals",
        location="Saudi Arabia",
        limit=10,
        fields=["name", "contact", "email"],
        request_id="brainit-task-1",
    )


def _success_body() -> dict[str, object]:
    return {
        "request_id": "brainit-task-1",
        "status": "completed",
        "execution_time": 1.23,
        "total": 2,
        "data": [{"name": "A"}, {"name": "B"}],
        "sources": [{"name": "source-1", "count": 2}],
        "errors": [],
        "quality": {
            "duplicates_removed": 0,
            "coverage": 0.9,
            "confidence": 0.8,
            "missing_fields": {"email": 1},
            "normalized_fields": 3,
        },
    }


@pytest.mark.asyncio
async def test_scraper_client_success_path():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/scrape"
        assert request.headers.get("X-API-Key") == "k"
        return httpx.Response(status_code=200, json=_success_body())

    client = ScraperClient(
        base_url="http://scraper.local",
        api_key="k",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )

    result = await client.scrape(_payload())
    assert result.status == "completed"
    assert result.total == 2
    assert result.quality.confidence == 0.8


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (401, "scraper_auth_error"),
        (403, "scraper_auth_error"),
        (422, "scraper_validation_error"),
        (503, "scraper_service_unavailable"),
    ],
)
async def test_scraper_client_maps_known_http_errors(status_code: int, expected_code: str):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status_code, json={"error": "boom"})

    client = ScraperClient(
        base_url="http://scraper.local",
        api_key="k",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ScraperClientError) as exc_info:
        await client.scrape(_payload())

    assert exc_info.value.code == expected_code
    assert exc_info.value.status_code == status_code


@pytest.mark.asyncio
async def test_scraper_client_handles_timeout():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client = ScraperClient(
        base_url="http://scraper.local",
        api_key="k",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ScraperClientError) as exc_info:
        await client.scrape(_payload())

    assert exc_info.value.code == "scraper_timeout"


@pytest.mark.asyncio
async def test_scraper_client_requires_api_key():
    client = ScraperClient(
        base_url="http://scraper.local",
        api_key="",
        timeout_seconds=1,
    )

    with pytest.raises(ScraperClientError) as exc_info:
        await client.scrape(_payload())

    assert exc_info.value.code == "scraper_auth_error"
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_scraper_client_rejects_invalid_response_contract():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, content=json.dumps({"status": "completed"}))

    client = ScraperClient(
        base_url="http://scraper.local",
        api_key="k",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ScraperClientError) as exc_info:
        await client.scrape(_payload())

    assert exc_info.value.code == "scraper_contract_error"
