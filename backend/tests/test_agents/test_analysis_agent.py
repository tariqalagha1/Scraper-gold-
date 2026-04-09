import sys
import types

import pytest

from app.agents.analysis_agent import AnalysisAgent
from app.config import settings


pytestmark = pytest.mark.asyncio


async def test_analysis_agent_uses_saved_openai_provider_key(monkeypatch):
    class FakeChatCompletions:
        async def create(self, **kwargs):
            FakeAsyncOpenAI.requests.append(kwargs)
            prompt = kwargs["messages"][1]["content"]
            if "`insights`" in prompt:
                content = (
                    '{"insights":[{"type":"trend","description":"AI insight",'
                    '"details":{"confidence":"high"}}]}'
                )
            else:
                content = (
                    '{"overview":"AI summary","key_points":["Point A"],'
                    '"content_types":{"unknown":1},"basis":"openai_summary"}'
                )
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=content))]
            )

    class FakeAsyncOpenAI:
        api_keys: list[str] = []
        requests: list[dict] = []

        def __init__(self, api_key: str):
            self.api_key = api_key
            FakeAsyncOpenAI.api_keys.append(api_key)
            self.chat = types.SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI))
    monkeypatch.setattr(settings, "ANALYSIS_MODE", "ai", raising=False)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "", raising=False)

    result = await AnalysisAgent().execute(
        {
            "items": [{"title": "Item One", "content": "Price is 10 dollars."}],
            "analysis_type": "both",
            "providers": {"openai": "user-openai-key"},
        }
    )

    assert result["status"] == "success"
    assert result["data"]["analysis_mode"] == "ai"
    assert result["data"]["analysis_provider"] == "openai"
    assert result["data"]["summary"]["mode"] == "ai"
    assert result["data"]["summary"]["overview"] == "AI summary"
    assert result["data"]["insights"][0]["mode"] == "ai"
    assert FakeAsyncOpenAI.api_keys == ["user-openai-key", "user-openai-key"]
    assert all(call["model"] == settings.OPENAI_ANALYSIS_MODEL for call in FakeAsyncOpenAI.requests)
