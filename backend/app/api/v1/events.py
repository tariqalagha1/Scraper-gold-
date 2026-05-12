import secrets
import json
from sqlalchemy import select
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.deps import verify_api_key
from app.config import settings
from app.db.session import async_session_factory
from app.models.api_key import ApiKey
from app.observability.event_emitter import get_latest_events, subscribe, unsubscribe
from app.services.saas import hash_api_key
from app.services.system_secrets import get_effective_system_secret

router = APIRouter()

@router.get("/latest", summary="Get latest events")
async def get_events(api_key: str = Depends(verify_api_key)):
    return {"events": get_latest_events()}

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    provided_api_key = (
        websocket.headers.get(settings.API_KEY_HEADER_NAME)
        or websocket.headers.get("x-api-key")
        or websocket.query_params.get("api_key")
        or ""
    ).strip()
    if not provided_api_key:
        await websocket.close(code=1008)
        return

    is_authorized = False
    async with async_session_factory() as db:
        expected_api_key = (await get_effective_system_secret(db, "API_KEY")).strip()
        if expected_api_key and secrets.compare_digest(provided_api_key, expected_api_key):
            is_authorized = True
        else:
            result = await db.execute(
                select(ApiKey.id).where(
                    ApiKey.key == hash_api_key(provided_api_key),
                    ApiKey.is_active.is_(True),
                )
            )
            is_authorized = result.scalar_one_or_none() is not None

    if not is_authorized:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    queue = await subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event))
    except WebSocketDisconnect:
        unsubscribe(queue)
    except Exception:
        unsubscribe(queue)
        await websocket.close()
