import time
import math
import logging
from collections import deque
from typing import Dict, List, Optional, Tuple
from core.scene_types import TrackContext, MotionFeatures, DistanceClass

logger = logging.getLogger(__name__)

class TemporalContextManager:
    """
    Bounded Temporal Context Engine for ASIS-V2.
    Tracks state history over time per object track with memory safety limits.
    Prevents memory leaks via TTL pruning and max_tracks bounding limits.
    """
    def __init__(self, max_history_frames: int = 150, max_tracks: int = 50, ttl_seconds: float = 30.0):
        self.max_history_frames = max_history_frames
        self.max_tracks = max_tracks
        self.ttl_seconds = ttl_seconds
        self.track_contexts: Dict[int, TrackContext] = {}
        self.history_buffers: Dict[int, deque] = {} # track_id -> deque of (frame_idx, center, bbox, velocity, timestamp)

    def update_track(
        self,
        track_id: int,
        class_id: int,
        frame_idx: int,
        bbox: List[float],
        motion_features: MotionFeatures,
        distance_class: str = DistanceClass.MEDIUM,
        occlusion_level: float = 0.0
    ) -> TrackContext:
        """
        Updates or registers a TrackContext entry and appends to bounded trajectory history.
        """
        x1, y1, x2, y2 = bbox
        center = [(x1 + x2) / 2.0, (y1 + y2) / 2.0]
        now = time.time()

        if track_id not in self.track_contexts:
            # Memory safety: Evict oldest stale track if budget reached
            if len(self.track_contexts) >= self.max_tracks:
                self._evict_oldest_track()

            context = TrackContext(
                track_id=track_id,
                class_id=class_id,
                age=1,
                last_seen_frame=frame_idx,
                bbox=bbox,
                center=center,
                motion_features=motion_features,
                distance_class=distance_class,
                occlusion_level=occlusion_level
            )
            self.track_contexts[track_id] = context
            self.history_buffers[track_id] = deque(maxlen=self.max_history_frames)
        else:
            context = self.track_contexts[track_id]
            context.age += 1
            context.last_seen_frame = frame_idx
            context.bbox = bbox
            context.center = center
            context.motion_features = motion_features
            context.distance_class = distance_class
            context.occlusion_level = occlusion_level

        # Append to bounded trajectory deque
        self.history_buffers[track_id].append((frame_idx, center, bbox, motion_features.normalized_velocity, now))

        return context

    def get_track_context(self, track_id: int) -> Optional[TrackContext]:
        return self.track_contexts.get(track_id)

    def get_all_contexts(self) -> List[TrackContext]:
        return list(self.track_contexts.values())

    def prune_stale_tracks(self, current_frame_idx: int, max_missing_frames: int = 45):
        """
        Prunes tracks that have not been updated within max_missing_frames or TTL duration.
        """
        stale_ids = []
        now = time.time()
        for track_id, ctx in self.track_contexts.items():
            missing_frames = current_frame_idx - ctx.last_seen_frame
            if missing_frames > max_missing_frames:
                stale_ids.append(track_id)
            elif self.history_buffers[track_id] and (now - self.history_buffers[track_id][-1][4]) > self.ttl_seconds:
                stale_ids.append(track_id)

        for tid in stale_ids:
            self.track_contexts.pop(tid, None)
            self.history_buffers.pop(tid, None)

    def _evict_oldest_track(self):
        """Evicts the least recently seen track to maintain memory budget."""
        if not self.track_contexts:
            return
        oldest_tid = min(self.track_contexts.keys(), key=lambda tid: self.track_contexts[tid].last_seen_frame)
        self.track_contexts.pop(oldest_tid, None)
        self.history_buffers.pop(oldest_tid, None)

    def get_trajectory_history(self, track_id: int) -> List[Tuple[int, List[float], List[float], float, float]]:
        """Returns list of (frame_idx, center, bbox, velocity, timestamp) for track_id."""
        buf = self.history_buffers.get(track_id)
        return list(buf) if buf else []
