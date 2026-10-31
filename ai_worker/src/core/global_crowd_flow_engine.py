import math
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional, Any
from core.scene_types import TrackContext, CameraMotionClass

logger = logging.getLogger(__name__)

class GlobalCrowdFlowEngine:
    """
    Global Crowd Flow & Coherence Engine for ASIS-V2.
    Extracts dominant crowd motion vectors, flow coherence, and subtracts global camera motion
    (pan/tilt/shake/zoom) to isolate true physical crowd movement from camera movement.
    """
    def __init__(self):
        pass

    def compute_flow(
        self,
        tracks: List[TrackContext],
        camera_motion_vector: Tuple[float, float] = (0.0, 0.0),
        camera_motion_class: str = CameraMotionClass.STATIC
    ) -> Dict[str, Any]:
        """
        Computes global crowd flow, flow coherence, and camera-compensated motion distribution.
        """
        persons = [t for t in tracks if t.class_id == 0]
        if not persons:
            return {
                "dominant_vector": [0.0, 0.0],
                "flow_coherence": 1.0,
                "camera_compensated": True if camera_motion_class == CameraMotionClass.STATIC else False,
                "active_moving_count": 0
            }

        cam_dx, cam_dy = camera_motion_vector

        # Subtract camera motion vector from person displacement
        comp_vectors = []
        for t in persons:
            mf = t.motion_features
            if mf.normalized_velocity < 0.2:
                continue

            # Apparent displacement vector in polar/Cartesian
            raw_dx = mf.displacement_px * math.cos(mf.direction_rad) if hasattr(mf, 'displacement_px') else 0.0
            raw_dy = mf.displacement_px * math.sin(mf.direction_rad) if hasattr(mf, 'displacement_px') else 0.0

            # Compensated vector
            cdx = raw_dx - cam_dx
            cdy = raw_dy - cam_dy
            comp_dist = math.hypot(cdx, cdy)

            if comp_dist > 0.1:
                comp_dir = math.atan2(cdy, cdx)
                comp_vectors.append((cdx, cdy, comp_dist, comp_dir))

        if not comp_vectors:
            return {
                "dominant_vector": [0.0, 0.0],
                "flow_coherence": 1.0,
                "camera_compensated": True,
                "active_moving_count": 0
            }

        # Dominant Vector & Flow Coherence
        tot_dx = sum(v[0] for v in comp_vectors)
        tot_dy = sum(v[1] for v in comp_vectors)
        count = float(len(comp_vectors))

        avg_dx = tot_dx / count
        avg_dy = tot_dy / count
        avg_mag = math.hypot(avg_dx, avg_dy)

        # Average of individual magnitudes
        mean_individual_mag = sum(v[2] for v in comp_vectors) / count
        coherence = round(avg_mag / (mean_individual_mag + 1e-5), 3) if mean_individual_mag > 0 else 1.0
        coherence = min(1.0, max(0.0, coherence))

        return {
            "dominant_vector": [round(avg_dx, 2), round(avg_dy, 2)],
            "flow_coherence": coherence,
            "camera_compensated": True,
            "active_moving_count": len(comp_vectors)
        }
