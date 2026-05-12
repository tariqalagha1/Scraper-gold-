import asyncio
from datetime import datetime, timezone
from collections import deque
from typing import Dict, Any, List, Set, Callable

EVENT_BUFFER = deque(maxlen=1000)
_SUBSCRIBERS: Set[asyncio.Queue] = set()

def emit(event_type: str, data: Dict[str, Any], trace_id: str) -> None:
    """Non-blocking fire-and-forget event emission."""
    event = {
        "trace_id": trace_id,
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data
    }
    
    EVENT_BUFFER.append(event)
    
    # Notify subscribers without blocking
    for queue in list(_SUBSCRIBERS):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass
        except Exception:
            _SUBSCRIBERS.discard(queue)

def get_latest_events() -> List[Dict[str, Any]]:
    return list(EVENT_BUFFER)

async def subscribe() -> asyncio.Queue:
    queue = asyncio.Queue(maxsize=100)
    _SUBSCRIBERS.add(queue)
    return queue

def unsubscribe(queue: asyncio.Queue) -> None:
    _SUBSCRIBERS.discard(queue)
