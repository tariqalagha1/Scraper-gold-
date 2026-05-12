"""HTTP client for Smart Scraper integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.schemas.scraper import ScraperTaskInputPayload, SmartScraperResponse


@dataclass
class ScraperClientError(Exception):
    message: str
    code: str
    status_code: int | None = None
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


class ScraperClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = str(base_url).rstrip("/")
        self.api_key = str(api_key or "").strip()
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self._transport = transport

    @classmethod
    def from_settings(cls) -> "ScraperClient":
        return cls(
            base_url=settings.SCRAPER_BASE_URL,
            api_key=settings.SCRAPER_API_KEY,
            timeout_seconds=settings.SCRAPER_TIMEOUT_SECONDS,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _ensure_configured(self) -> None:
        if not self.api_key:
            raise ScraperClientError(
                message="Smart Scraper API key is not configured.",
                code="scraper_auth_error",
                status_code=401,
            )

    async def scrape(self, payload: ScraperTaskInputPayload) -> SmartScraperResponse:
        self._ensure_configured()
        
        url = f"{self.base_url}/api/v1/scrape"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    url,
                    headers=self._headers(),
                    json=payload.model_dump(exclude_none=True),
                )
        except httpx.TimeoutException as exc:
            raise ScraperClientError(
                message="Smart Scraper request timed out.",
                code="scraper_timeout",
                details={"reason": str(exc)},
            ) from exc
        except httpx.RequestError as exc:
            raise ScraperClientError(
                message="Cannot reach Smart Scraper service.",
                code="scraper_unreachable",
                details={"reason": str(exc)},
            ) from exc

        body: dict[str, Any] = {}
        try:
            parsed = response.json()
            body = parsed if isinstance(parsed, dict) else {}
        except Exception:
            body = {}

        if response.status_code == 401:
            raise ScraperClientError(
                message="Smart Scraper authentication failed (missing API key).",
                code="scraper_auth_error",
                status_code=401,
                details=body,
            )
        if response.status_code == 403:
            raise ScraperClientError(
                message="Smart Scraper authorization failed (invalid API key).",
                code="scraper_auth_error",
                status_code=403,
                details=body,
            )
        if response.status_code == 422:
            raise ScraperClientError(
                message="Smart Scraper rejected request payload.",
                code="scraper_validation_error",
                status_code=422,
                details=body,
            )
        if response.status_code == 503:
            raise ScraperClientError(
                message="Smart Scraper service unavailable.",
                code="scraper_service_unavailable",
                status_code=503,
                details=body,
            )
        if response.status_code >= 400:
            raise ScraperClientError(
                message=f"Smart Scraper returned unexpected status code {response.status_code}.",
                code="scraper_http_error",
                status_code=response.status_code,
                details=body,
            )

        try:
            return SmartScraperResponse.model_validate(body)
        except Exception as exc:
            raise ScraperClientError(
                message="Smart Scraper response did not match expected contract.",
                code="scraper_contract_error",
                status_code=response.status_code,
                details={"response_body": body},
            ) from exc

    async def check_health(self) -> str:
        if not self.base_url:
            return "unconfigured"
        url = f"{self.base_url}/health"
        try:
            async with httpx.AsyncClient(
                timeout=min(self.timeout_seconds, 5.0),
                transport=self._transport,
            ) as client:
                response = await client.get(url)
            if response.status_code == 200:
                return "reachable"
            return "unreachable"
        except Exception:
            return "unreachable"
