from collections import deque
import logging

logger = logging.getLogger(__name__)

class TemporalBuffer:
    def __init__(self, max_len: int = 300):
        # Default max_len of 300 frames (e.g., 30 seconds at 10 FPS)
        self.buffer = deque(maxlen=max_len)
        self.max_len = max_len

    def add_frame_data(self, frame_index: int, tracks: list):
        """
        Add track data for a single frame.
        tracks should be a list of dictionaries with bounding box, ID, class, etc.
        """
        self.buffer.append({
            "frame_index": frame_index,
            "tracks": tracks
        })

    def get_track_history(self, track_id: int) -> list:
        """
        Extract the history of a specific track_id across the temporal window.
        """
        history = []
        for frame_data in self.buffer:
            for track in frame_data["tracks"]:
                if track["track_id"] == track_id:
                    history.append(track)
                    break
        return history

    def clear(self):
        self.buffer.clear()
