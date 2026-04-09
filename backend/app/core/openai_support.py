from __future__ import annotations

import json
from typing import Any

from app.config import settings


def resolve_openai_api_key(providers: Any = None) -> str:
    provider_values = providers if isinstance(providers, dict) else {}
    provider_key = str(provider_values.get("openai") or "").strip()
    if provider_key:
        return provider_key
    return settings.OPENAI_API_KEY.strip()


async def request_openai_json(
    *,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.2,
) -> dict[str, Any]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(strip_json_fence(content))


def strip_json_fence(content: str) -> str:
    value = str(content or "").strip()
    if value.startswith("```"):
        value = value.strip("`")
        if value.lower().startswith("json"):
            value = value[4:]
    return value.strip()
