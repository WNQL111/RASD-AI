import json
import logging
from typing import Dict, Any, Optional, Set
from collections import deque

logger = logging.getLogger(__name__)

class EventProcessor:
    """
    Idempotent Event Processor for ASIS-V2 Backend.
    Validates EventEnvelope schema, enforces event deduplication via event_id lookup,
    handles sequence ordering, and coordinates persistence before realtime SSE broadcast.
    """
    def __init__(self, max_history_capacity: int = 1000):
        self.max_history_capacity = max_history_capacity
        self.seen_event_ids: Set[str] = set()
        self.seen_event_queue: deque = deque()
        self.last_sequence_by_camera: Dict[str, int] = {}

    def is_duplicate(self, event_id: str) -> bool:
        """
        Checks whether the event_id has already been processed (Idempotency).
        """
        if not event_id:
            return False

        if event_id in self.seen_event_ids:
            return True

        if len(self.seen_event_queue) >= self.max_history_capacity:
            oldest = self.seen_event_queue.popleft()
            self.seen_event_ids.discard(oldest)

        self.seen_event_ids.add(event_id)
        self.seen_event_queue.append(event_id)
        return False

    def validate_schema(self, payload: Dict[str, Any]) -> bool:
        """
        Validates whether payload conforms to standard EventEnvelope schema.
        """
        required_fields = ["type", "timestamp"]
        for field in required_fields:
            if field not in payload:
                logger.warning(f"EventProcessor: Invalid event payload - missing field '{field}'")
                return False
        return True

    def process_incoming_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Main entry point for incoming Redis bus messages.
        Returns validated, deduplicated payload ready for broadcast & persistence, or None if invalid/duplicate.
        """
        if not self.validate_schema(payload):
            return None

        event_id = payload.get("event_id")
        if event_id and self.is_duplicate(event_id):
            logger.info(f"EventProcessor: Duplicate event #{event_id} ignored.")
            return None

        # Sequence ordering tracking
        camera_id = str(payload.get("camera_id") or payload.get("video_id") or "global")
        seq = payload.get("sequence", 1)
        last_seq = self.last_sequence_by_camera.get(camera_id, 0)
        if seq > last_seq:
            self.last_sequence_by_camera[camera_id] = seq

        return payload

# Singleton EventProcessor Instance
event_processor = EventProcessor()
