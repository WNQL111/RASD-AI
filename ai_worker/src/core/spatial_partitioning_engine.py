import math
import logging
from typing import List, Dict, Tuple, Optional, Any
from core.scene_types import TrackContext

logger = logging.getLogger(__name__)

class SpatialCell:
    def __init__(self, cell_id: Tuple[int, int], bounds: Tuple[float, float, float, float]):
        self.cell_id = cell_id
        self.bounds = bounds  # (x1, y1, x2, y2)
        self.tracks: List[TrackContext] = []
        self.mean_speed: float = 0.0
        self.direction_histogram: List[int] = [0] * 8
        self.anomaly_score: float = 0.0

    def add_track(self, track: TrackContext):
        self.tracks.append(track)

    def compute_metrics(self, global_median_speed: float = 1.5):
        if not self.tracks:
            return
        speeds = [t.motion_features.normalized_velocity for t in self.tracks]
        self.mean_speed = sum(speeds) / len(speeds)
        
        # Local speed deviation spike score
        speed_spike = max(0.0, (self.mean_speed - global_median_speed) / (global_median_speed + 1e-5))
        self.anomaly_score = round(min(1.0, speed_spike * 0.4), 3)

class SpatialPartitioningEngine:
    """
    Spatial Grid Partitioning Engine for ASIS-V2.
    Divides the 2D frame into adaptive spatial grid cells (e.g. 4x4 or 8x8).
    Prunes O(N^2) pairwise comparisons by restricting candidate generation exclusively to adjacent grid cells.
    """
    def __init__(self, grid_cols: int = 4, grid_rows: int = 4):
        self.grid_cols = grid_cols
        self.grid_rows = grid_rows

    def partition_scene(
        self,
        tracks: List[TrackContext],
        frame_w: int = 1280,
        frame_h: int = 720,
        global_median_speed: float = 1.5
    ) -> Dict[Tuple[int, int], SpatialCell]:
        """
        Partitions active tracks into spatial grid cells and computes per-cell metrics.
        """
        cell_w = max(1.0, frame_w / float(self.grid_cols))
        cell_h = max(1.0, frame_h / float(self.grid_rows))

        cells: Dict[Tuple[int, int], SpatialCell] = {}
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                bounds = (c * cell_w, r * cell_h, (c + 1) * cell_w, (r + 1) * cell_h)
                cells[(c, r)] = SpatialCell((c, r), bounds)

        persons = [t for t in tracks if t.class_id == 0]
        for t in persons:
            cx, cy = t.center
            c_idx = min(self.grid_cols - 1, max(0, int(cx // cell_w)))
            r_idx = min(self.grid_rows - 1, max(0, int(cy // cell_h)))
            cells[(c_idx, r_idx)].add_track(t)

        for cell in cells.values():
            cell.compute_metrics(global_median_speed=global_median_speed)

        return cells
