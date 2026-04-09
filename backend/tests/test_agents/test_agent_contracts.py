import asyncio

import pytest

from app.agents.analysis_agent import AnalysisAgent
from app.agents.base_agent import REDACTED_VALUE, BaseAgent
from app.agents.intake_agent import IntakeAgent

@pytest.mark.asyncio
async def test_intake_and_analysis_include_required_metadata():
    intake = await IntakeAgent().safe_execute({"url": "https://example.com", "scrape_type": "general"})
    analysis = await AnalysisAgent().safe_execute(
        {"items": [{"type": "processed_page", "title": "Example", "content": "Example content"}]}
    )

    for result, agent_name in ((intake, "intake_agent"), (analysis, "analysis_agent")):
        assert result["status"] == "success"
        assert result["metadata"]["agent"] == agent_name
        assert "timestamp" in result["metadata"]
        assert "source" in result["metadata"]
        assert "type" in result["metadata"]
        assert "execution_time" in result["metadata"]


def test_log_payload_redacts_sensitive_fields_recursively():
    payload = {
        "credentials": {
            "username": "user@example.com",
            "password": "super-secret",
            "nested": {
                "token": "abc123",
                "profile": [
                    {"api_key": "key-1"},
                    {"authorization": "Bearer secret"},
                ],
            },
        },
        "items": [
            {"login": {"password": "another-secret"}},
            {"safe": "value"},
        ],
    }

    redacted = BaseAgent._prepare_log_payload(payload)

    assert redacted["credentials"] == REDACTED_VALUE
    assert redacted["items"][0]["login"] == REDACTED_VALUE
    assert redacted["items"][1]["safe"] == "value"
    serialized = str(redacted)
    assert "super-secret" not in serialized
    assert "abc123" not in serialized
    assert "key-1" not in serialized
    assert "Bearer secret" not in serialized


@pytest.mark.asyncio
async def test_agent_logging_and_persistence_receive_redacted_payloads(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_persist(self, **kwargs):
        captured["persist"] = kwargs

    def fake_log_agent_action(**kwargs):
        captured["log_action"] = kwargs

    monkeypatch.setattr(BaseAgent, "_persist_log", fake_persist)

    agent = IntakeAgent()
    monkeypatch.setattr(agent.logger, "log_agent_action", fake_log_agent_action)

    await agent.safe_execute(
        {
            "url": "https://example.com",
            "credentials": {
                "username": "user@example.com",
                "password": "super-secret",
                "token": "token-123",
            },
            "login": {"authorization": "Bearer sensitive"},
        }
    )
    await asyncio.sleep(0)

    log_action = captured["log_action"]
    persisted = captured["persist"]

    assert log_action["input_data"]["credentials"] == REDACTED_VALUE
    assert log_action["input_data"]["login"] == REDACTED_VALUE
    assert persisted["input_data"]["credentials"] == REDACTED_VALUE
    assert persisted["input_data"]["login"] == REDACTED_VALUE

    assert "super-secret" not in str(log_action)
    assert "token-123" not in str(log_action)
    assert "Bearer sensitive" not in str(log_action)
    assert "super-secret" not in str(persisted)
    assert "token-123" not in str(persisted)
    assert "Bearer sensitive" not in str(persisted)
