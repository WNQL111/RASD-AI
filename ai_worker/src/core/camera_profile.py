from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class CameraProfile:
    camera_id: str
    scene_type: str = 'UNKNOWN'
    location_type: str = 'INDOOR'
    expected_density: str = 'MEDIUM'
    expected_flow: str = 'PEDESTRIAN'
    expected_activity: str = 'WALKING'
    allowed_regions: List[List[float]] = field(default_factory=list)
    restricted_regions: List[List[float]] = field(default_factory=list)
    perspective_scale_factor: float = 1.0
    camera_motion_type: str = 'STATIONARY'

    @staticmethod
    def default_profile(camera_id: str = 'default') -> 'CameraProfile':
        return CameraProfile(camera_id=camera_id, scene_type='UNKNOWN')
