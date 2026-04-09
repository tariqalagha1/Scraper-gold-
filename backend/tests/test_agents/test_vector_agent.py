import sys
import types

import pytest

from app.agents.vector_agent import VectorAgent
from app.config import settings


pytestmark = pytest.mark.asyncio


async def test_vector_agent_uses_saved_openai_provider_key(monkeypatch):
    class FakeEmbeddings:
        async def create(self, **kwargs):
            FakeAsyncOpenAI.requests.append(kwargs)
            return types.SimpleNamespace(
                data=[types.SimpleNamespace(embedding=[0.1, 0.2, 0.3])]
            )

    class FakeAsyncOpenAI:
        api_keys: list[str] = []
        requests: list[dict] = []

        def __init__(self, api_key: str):
            self.api_key = api_key
            FakeAsyncOpenAI.api_keys.append(api_key)
            self.embeddings = FakeEmbeddings()

    from app.agents import vector_agent as vector_agent_module

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI))
    monkeypatch.setattr(vector_agent_module, "vector_store_enabled", lambda: True)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "", raising=False)

    result = await VectorAgent().execute(
        {
            "operation": "embed",
            "items": [{"title": "Example embedded text"}],
            "providers": {"openai": "user-openai-key"},
        }
    )

    assert result["status"] == "success"
    assert result["data"]["provider"] == "openai"
    assert result["data"]["embeddings_generated"] == 1
    assert FakeAsyncOpenAI.api_keys == ["user-openai-key"]
    assert FakeAsyncOpenAI.requests[0]["model"] == settings.OPENAI_EMBEDDING_MODEL
