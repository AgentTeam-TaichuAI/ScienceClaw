"""Global in-memory notification bus for real-time session updates.

Uses asyncio queues to fan out lightweight events to all connected SSE clients.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator, Dict, Optional

from loguru import logger

_subscribers: Dict[int, asyncio.Queue] = {}
_next_id = 0
_lock = asyncio.Lock()


async def subscribe(*, max_queue: int = 256) -> tuple[int, AsyncIterator[Dict[str, Any]]]:
    """Register a new subscriber. Returns (subscriber_id, async event iterator)."""
    global _next_id
    async with _lock:
        sub_id = _next_id
        _next_id += 1
        q: asyncio.Queue = asyncio.Queue(maxsize=max_queue)
        _subscribers[sub_id] = q

    async def _iter() -> AsyncIterator[Dict[str, Any]]:
        try:
            while True:
                event = await q.get()
                if event is None:
                    break
                yield event
        finally:
            async with _lock:
                _subscribers.pop(sub_id, None)

    return sub_id, _iter()


async def unsubscribe(sub_id: int) -> None:
    """Remove a subscriber and signal its iterator to stop."""
    async with _lock:
        q = _subscribers.pop(sub_id, None)
    if q is not None:
        try:
            q.put_nowait(None)
        except asyncio.QueueFull:
            pass


def publish(event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Fan out an event to all connected subscribers (non-blocking)."""
    event = {
        "event": event_type,
        "data": {**(data or {}), "timestamp": int(time.time())},
    }
    stale: list[int] = []
    for sub_id, q in list(_subscribers.items()):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            stale.append(sub_id)

    for sub_id in stale:
        _subscribers.pop(sub_id, None)
        logger.warning(f"[Notifications] Dropped slow subscriber {sub_id}")
