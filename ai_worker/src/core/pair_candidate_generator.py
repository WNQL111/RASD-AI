import math
import logging
from typing import List, Tuple, Dict
from core.scene_types import TrackContext
from core.interaction_types import InteractionPair, DistanceRelation

logger = logging.getLogger(__name__)

class PairCandidateGenerator:
    """
    Bounded Pair Candidate Generator for ASIS-V2.
    Prunes O(N^2) pairwise comparisons using spatial grid bucketing and distance thresholding.
    Enforces a strict upper bound max_pairs = 30 to guarantee sub-millisecond execution.
    """
    def __init__(self, proximity_radius_px: float = 180.0, max_pairs: int = 30):
        self.proximity_radius_px = proximity_radius_px
        self.max_pairs = max_pairs

    def generate_candidates(self, tracks: List[TrackContext]) -> List[InteractionPair]:
        """
        Generates interaction candidate pairs from active track contexts.
        """
        persons = [t for t in tracks if t.class_id == 0]
        n = len(persons)
        if n < 2:
            return []

        # Spatial Grid Bucketing for fast pruning
        cell_size = self.proximity_radius_px
        grid: Dict[Tuple[int, int], List[TrackContext]] = {}

        for t in persons:
            cx, cy = t.center
            cell_x = int(cx // cell_size)
            cell_y = int(cy // cell_size)
            key = (cell_x, cell_y)
            if key not in grid:
                grid[key] = []
            grid[key].append(t)

        candidate_pairs: List[InteractionPair] = []
        seen_pairs = set()

        for (cell_x, cell_y), cell_tracks in grid.items():
            # Check current cell and neighboring cells (3x3 grid neighborhood)
            neighbor_keys = [
                (cell_x + dx, cell_y + dy)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            ]
            for nkey in neighbor_keys:
                if nkey not in grid:
                    continue
                for t1 in cell_tracks:
                    for t2 in grid[nkey]:
                        if t1.track_id >= t2.track_id:
                            continue
                        pair_id = (t1.track_id, t2.track_id)
                        if pair_id in seen_pairs:
                            continue
                        seen_pairs.add(pair_id)

                        dist = math.hypot(t1.center[0] - t2.center[0], t1.center[1] - t2.center[1])
                        if dist <= self.proximity_radius_px:
                            candidate_pairs.append(InteractionPair(
                                track_id_a=t1.track_id,
                                track_id_b=t2.track_id,
                                center_distance_px=round(dist, 2)
                            ))

                            if len(candidate_pairs) >= self.max_pairs:
                                return candidate_pairs

        return candidate_pairs
