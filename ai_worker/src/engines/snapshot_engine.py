import os
import cv2
import logging

logger = logging.getLogger(__name__)

class SnapshotEngine:
    """Captures and saves event snapshots to the static serving folder."""
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            candidates = [
                "/app/data/videos/snapshots",
                os.path.join(os.getcwd(), "data", "videos", "snapshots"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "videos", "snapshots")
            ]
            resolved = candidates[0]
            for c in candidates:
                if os.path.exists(os.path.dirname(c)) or os.path.exists(c):
                    resolved = c
                    break
            self.output_dir = resolved
        else:
            self.output_dir = output_dir
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create snapshot directory: {e}")

    def capture_snapshot(self, frame, event_id: str, *args, **kwargs) -> str:
        filename = f"{event_id}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        try:
            cv2.imwrite(filepath, frame)
            logger.info(f"Snapshot saved: {filepath}")
            # Returns path relative to static serving mount (/videos)
            return f"/videos/snapshots/{filename}"
        except Exception as e:
            logger.error(f"Error saving event snapshot: {e}")
            return ""

    def save_snapshot(self, frame, event_id: str, *args, **kwargs) -> str:
        return self.capture_snapshot(frame, event_id, *args, **kwargs)

    def save_event_snapshot(self, frame, event_id: str, *args, **kwargs) -> str:
        return self.capture_snapshot(frame, event_id, *args, **kwargs)
