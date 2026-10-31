import math
import logging
from typing import List, Tuple
from core.scene_types import TrackContext
from core.interaction_types import InteractionPair, DistanceRelation

logger = logging.getLogger(__name__)

class SpatialRelationshipEngine:
    """
    Spatial Relationship Engine for ASIS-V2.
    Calculates scale-normalized spatial distance and 2D bounding box IoU overlap between track pairs.
    """
    def compute_spatial_relation(
        self,
        pair: InteractionPair,
        track_a: TrackContext,
        track_b: TrackContext
    ) -> InteractionPair:
        """
        Updates pair with scale-normalized distance and IoU overlap.
        """
        # 1. Bounding Box Area Normalization
        ax1, ay1, ax2, ay2 = track_a.bbox
        bx1, by1, bx2, by2 = track_b.bbox

        area_a = max(1.0, (ax2 - ax1) * (ay2 - ay1))
        area_b = max(1.0, (bx2 - bx1) * (by2 - by1))
        geometric_mean_scale = math.sqrt(math.sqrt(area_a) * math.sqrt(area_b))

        # Normalized distance relative to body scale
        norm_dist = pair.center_distance_px / max(1.0, geometric_mean_scale)
        pair.normalized_distance = round(norm_dist, 3)

        # 2. 2D Bounding Box IoU Overlap
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        intersection_area = iw * ih

        union_area = area_a + area_b - intersection_area
        iou = intersection_area / union_area if union_area > 0 else 0.0
        pair.iou_overlap = round(iou, 3)
        pair.overlap_score = round(min(1.0, iou * 3.0), 3)

        # 3. Automatic Relative Distance Categorization
        if iou > 0.15:
            pair.distance_class = DistanceRelation.OVERLAPPING
        elif norm_dist < 0.45:
            pair.distance_class = DistanceRelation.VERY_NEAR
        elif norm_dist < 0.85:
            pair.distance_class = DistanceRelation.NEAR
        elif norm_dist < 1.50:
            pair.distance_class = DistanceRelation.MEDIUM
        elif norm_dist < 2.50:
            pair.distance_class = DistanceRelation.FAR
        else:
            pair.distance_class = DistanceRelation.VERY_FAR

        return pair
