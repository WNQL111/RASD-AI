import time
import logging
from collections import deque
from typing import Optional, Tuple
from core.resource_types import FrameIngressItem

logger = logging.getLogger(__name__)

class BackpressureController:
    """
    Backpressure & Queue Controller for ASIS-V2.
    Manages bounded frame ingress queue (max_queue_size = 30).
    Enforces stale frame drop policy (frame_age > 200ms) for low-value frames.
    NEVER drops critical event evidence frames.
    """
    def __init__(self, max_queue_size: int = 30, max_age_ms: float = 200.0):
        self.max_queue_size = max_queue_size
        self.max_age_ms = max_age_ms
        self.queue: deque = deque()
        self.total_dropped_count = 0

    def enqueue_frame(
        self,
        frame_id: int,
        camera_id: str,
        frame_data: any,
        is_critical: bool = False
    ) -> bool:
        """
        Enqueues a new frame into the bounded queue. Drops stale low-priority frames if full.
        """
        now = time.time()
        item = FrameIngressItem(
            frame_id=frame_id,
            camera_id=camera_id,
            timestamp=now,
            frame_data=frame_data,
            is_critical_evidence=is_critical
        )

        if len(self.queue) >= self.max_queue_size:
            # Queue Full -> Apply Stale Drop Policy
            dropped = self._drop_stale_non_critical_frame()
            if not dropped:
                # Unable to drop non-critical frame (queue full of critical evidence)
                logger.warning("BackpressureController: Queue full with critical evidence. Enqueue deferred.")
                return False

        self.queue.append(item)
        return True

    def dequeue_frame(self) -> Optional[FrameIngressItem]:
        """
        Dequeues the next frame for processing. Drops stale non-critical frames automatically.
        """
        now = time.time()
        while self.queue:
            item = self.queue.popleft()
            age_ms = (now - item.timestamp) * 1000.0
            item.age_ms = round(age_ms, 2)

            if age_ms > self.max_age_ms and not item.is_critical_evidence:
                self.total_dropped_count += 1
                logger.debug(f"BackpressureController: Dropped stale frame #{item.frame_id} (Age: {item.age_ms}ms)")
                continue

            return item
        return None

    def _drop_stale_non_critical_frame(self) -> bool:
        # Search from left (oldest) for first non-critical frame to drop
        for idx in range(len(self.queue)):
            if not self.queue[idx].is_critical_evidence:
                del self.queue[idx]
                self.total_dropped_count += 1
                return True
        return False

    def get_queue_depth(self) -> int:
        return len(self.queue)
