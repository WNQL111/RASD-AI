import queue
import logging

logger = logging.getLogger(__name__)

class FrameQueue:
    """
    Thread-safe double-buffered frame queue with automated frame drop.
    Prevents latency accumulation when AI processing time exceeds frame rate.
    """
    def __init__(self, maxsize: int = 15):
        self.queue = queue.Queue(maxsize=maxsize)

    def put(self, frame_idx: int, frame) -> bool:
        try:
            # Non-blocking put; if full, raise queue.Full exception and drop frame
            self.queue.put_nowait((frame_idx, frame))
            return True
        except queue.Full:
            # Drop older frames if the processing is falling behind
            try:
                dropped = self.queue.get_nowait()
                logger.warning(f"⚠️ Process queue saturated. Dropped frame index: {dropped[0]}")
                self.queue.put_nowait((frame_idx, frame))
                return True
            except queue.Empty:
                return False

    def get(self):
        try:
            return self.queue.get(timeout=1.0)
        except queue.Empty:
            return None

    def empty(self) -> bool:
        return self.queue.empty()

    def size(self) -> int:
        return self.queue.qsize()
