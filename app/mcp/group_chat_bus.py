"""
Group Chat Event Bus
====================
Leichtgewichtiger in-memory Pub/Sub für Group Chat Events.
Kein zirkulärer Import: group_chat_auto_response.py pusht hier rein,
mcp.py subscribed und leitet an SSE-Sessions weiter.

Usage:
    # Publisher (group_chat_auto_response.py):
    from app.mcp.group_chat_bus import gc_bus
    await gc_bus.publish(session_id, sender, content, msg_type)

    # Subscriber (mcp.py / SSE-Handler):
    from app.mcp.group_chat_bus import gc_bus
    async with gc_bus.subscribe() as queue:
        event = await queue.get()
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Set

logger = logging.getLogger("ailinux.mcp.group_chat_bus")


class GroupChatBus:
    """Einfacher broadcast Bus: n Publisher → m Subscriber (asyncio.Queue)."""

    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()

    async def publish(
        self,
        session_id: str,
        sender: str,
        content: str,
        msg_type: str = "response",
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        """Broadcast Event an alle aktiven Subscriber."""
        if not self._subscribers:
            return
        event = {
            "event": "group_chat_message",
            "session_id": session_id,
            "sender": sender,
            "type": msg_type,
            "content": content,
            "metadata": metadata or {},
        }
        dead = set()
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.add(q)
            except Exception as e:
                logger.warning(f"Bus publish error: {e}")
                dead.add(q)
        # Tote Queues aufräumen
        self._subscribers -= dead
        if dead:
            logger.debug(f"Removed {len(dead)} dead subscribers")

    @asynccontextmanager
    async def subscribe(self, maxsize: int = 100):
        """Context-Manager: gibt eine Queue zurück, entfernt sie beim Exit."""
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._subscribers.add(q)
        logger.debug(f"Subscriber added ({len(self._subscribers)} total)")
        try:
            yield q
        finally:
            self._subscribers.discard(q)
            logger.debug(f"Subscriber removed ({len(self._subscribers)} remaining)")

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Singleton
gc_bus = GroupChatBus()
