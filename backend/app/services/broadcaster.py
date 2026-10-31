import asyncio
import json
import logging
from collections import deque
from typing import Set, List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class BroadcasterManager:
    """
    Lightweight, thread-safe SSE Broadcaster Manager.
    Supports multiple concurrent SSE subscribers with non-blocking broadcast,
    bounded queues (maxsize 100) to prevent memory leaks, event history buffer for Last-Event-ID resync,
    and automatic client cleanup.
    """
    def __init__(self, history_limit: int = 100):
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        self._event_history: deque = deque(maxlen=history_limit)

    async def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.add(queue)
            logger.info(f"SSE Broadcaster: New client subscribed. Total active clients: {len(self._subscribers)}")
        return queue

    async def unsubscribe(self, queue: asyncio.Queue):
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)
                logger.info(f"SSE Broadcaster: Client unsubscribed. Total active clients: {len(self._subscribers)}")

    async def get_events_since(self, last_event_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves missing events from history buffer since last_event_id for resync.
        """
        async with self._lock:
            history = list(self._event_history)
        
        found = False
        resync_events = []
        for ev in history:
            if found:
                resync_events.append(ev)
            elif str(ev.get("event_id") or ev.get("id")) == last_event_id:
                found = True
        
        return resync_events if found else history[-10:] if history else []

    async def broadcast(self, data: dict):
        async with self._lock:
            self._event_history.append(data)
            subscribers = list(self._subscribers)

        if not subscribers:
            return

        payload = json.dumps(data)
        for queue in subscribers:
            try:
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(payload)
            except Exception as e:
                logger.warning(f"SSE Broadcaster: Failed to push to subscriber queue: {e}")

    def broadcast_sync(self, data: dict):
        try:
            self._event_history.append(data)
            subscribers = list(self._subscribers)
            if not subscribers:
                return
            payload = json.dumps(data)
            for queue in subscribers:
                try:
                    if queue.full():
                        try:
                            queue.get_nowait()
                        except Exception:
                            pass
                    queue.put_nowait(payload)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"SSE Broadcaster broadcast_sync error: {e}")

# Global singleton broadcaster instance
broadcaster = BroadcasterManager()
