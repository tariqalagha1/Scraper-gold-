"""In-process agent registry for orchestrator routing."""
from __future__ import annotations

from app.config import settings
from app.schemas.scraper import AgentRegistryEntry


_AGENT_REGISTRY: dict[str, AgentRegistryEntry] = {}


def seed_agent_registry() -> None:
    if "scraper_agent" not in _AGENT_REGISTRY:
        base = str(settings.SCRAPER_BASE_URL).rstrip("/")
        _AGENT_REGISTRY["scraper_agent"] = AgentRegistryEntry(
            name="scraper_agent",
            description="Calls Smart Scraper service through API key",
            supported_task_types=["scrape", "lead_generation", "market_scan"],
            service_identifier="smart-scraper",
            endpoint=f"{base}/api/v1/scrape",
            health_url=f"{base}/health",
            status="enabled",
            enabled=True,
        )


def get_agent_registry_entry(name: str) -> AgentRegistryEntry | None:
    seed_agent_registry()
    return _AGENT_REGISTRY.get(str(name).strip())


def resolve_agent_for_task(task_type: str) -> AgentRegistryEntry | None:
    seed_agent_registry()
    normalized = str(task_type or "").strip().lower()
    for entry in _AGENT_REGISTRY.values():
        if normalized in {item.strip().lower() for item in entry.supported_task_types} and entry.enabled:
            return entry
    return None


def list_agent_registry_entries() -> list[AgentRegistryEntry]:
    seed_agent_registry()
    return list(_AGENT_REGISTRY.values())
