"""Execution contract schema and capability helpers.

Defines a strict contract for run execution so UI configuration,
backend validation, and runtime behavior stay aligned.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CORE_AGENTS: list[str] = [
    "policy_service",
    "strategic_execution_service",
    "multi_source_service",
    "quality_layer",
    "event_emitter",
    "control_service",
]
OPTIONAL_AGENTS: list[str] = [
    "analysis_agent",
    "vector_agent",
    "export_agent",
]
SUPPORTED_EXECUTION_MODES: list[str] = ["single_source", "multi_source"]
SUPPORTED_SOURCES: list[str] = ["internal", "google_maps", "web"]


class ExecutionControls(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fallback: bool = Field(default=True)
    early_stop: bool = Field(default=True)
    retry: bool = Field(default=True)


class ExecutionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agents: list[str] = Field(default_factory=lambda: list(CORE_AGENTS), min_length=1)
    optional_agents: list[str] = Field(default_factory=list)
    execution_mode: Literal["single_source", "multi_source"] = Field(default="multi_source")
    sources: list[str] = Field(default_factory=lambda: list(SUPPORTED_SOURCES), min_length=1)
    limit: int = Field(default=50, ge=1, le=100)
    controls: ExecutionControls = Field(default_factory=ExecutionControls)

    @model_validator(mode="after")
    def _validate_contract(self) -> "ExecutionContract":
        declared_agents = [str(item).strip() for item in self.agents if str(item).strip()]
        if declared_agents != CORE_AGENTS:
            raise ValueError(
                "agents must exactly match the supported core execution chain "
                f"{CORE_AGENTS}"
            )
        self.agents = declared_agents

        optional = [str(item).strip() for item in self.optional_agents if str(item).strip()]
        unknown_optional = [item for item in optional if item not in OPTIONAL_AGENTS]
        if unknown_optional:
            raise ValueError(
                f"optional_agents contains unsupported values: {unknown_optional}"
            )
        self.optional_agents = sorted(set(optional), key=optional.index)

        sources = [str(item).strip() for item in self.sources if str(item).strip()]
        if not sources:
            raise ValueError("sources must include at least one source")

        unknown_sources = [item for item in sources if item not in SUPPORTED_SOURCES]
        if unknown_sources:
            raise ValueError(f"sources contains unsupported values: {unknown_sources}")

        deduped_sources = sorted(set(sources), key=sources.index)
        if self.execution_mode == "single_source" and len(deduped_sources) != 1:
            raise ValueError("single_source mode requires exactly one source")
        if self.execution_mode == "multi_source" and len(deduped_sources) < 1:
            raise ValueError("multi_source mode requires at least one source")

        self.sources = deduped_sources
        return self


def build_execution_contract_from_job_config(
    config: dict[str, Any] | None,
    *,
    job_url: str | None = None,
) -> ExecutionContract:
    job_config = dict(config or {})

    raw_sources = job_config.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        configured_source_type = str(job_config.get("source_type") or "").strip()
        if configured_source_type in SUPPORTED_SOURCES:
            raw_sources = [configured_source_type]
        elif str(job_url or "").strip():
            raw_sources = ["web"]
        else:
            raw_sources = list(SUPPORTED_SOURCES)
    sources = [str(item).strip() for item in raw_sources if str(item).strip()]
    if not sources:
        sources = list(SUPPORTED_SOURCES)

    mode = "single_source" if len(sources) == 1 else "multi_source"

    raw_limit = job_config.get("max_records") or job_config.get("limit") or 50
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(100, limit))

    controls_obj = job_config.get("execution_controls")
    controls_dict = controls_obj if isinstance(controls_obj, dict) else {}

    return ExecutionContract(
        agents=list(CORE_AGENTS),
        optional_agents=[
            str(item).strip()
            for item in (job_config.get("optional_agents") or [])
            if str(item).strip() in OPTIONAL_AGENTS
        ],
        execution_mode=mode,
        sources=sources,
        limit=limit,
        controls=ExecutionControls(
            fallback=bool(controls_dict.get("fallback", True)),
            early_stop=bool(controls_dict.get("early_stop", True)),
            retry=bool(controls_dict.get("retry", True)),
        ),
    )


def build_system_capabilities() -> dict[str, Any]:
    return {
        "execution_contract": {
            "agents": list(CORE_AGENTS),
            "optional_agents": list(OPTIONAL_AGENTS),
            "execution_modes": list(SUPPORTED_EXECUTION_MODES),
            "sources": list(SUPPORTED_SOURCES),
            "limit": {"min": 1, "max": 100, "default": 50},
            "controls": {
                "fallback": True,
                "early_stop": True,
                "retry": True,
            },
        }
    }
