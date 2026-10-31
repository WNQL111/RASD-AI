from typing import Dict, Any, Optional
from .camera_profile import CameraProfile

class CameraContextEngine:
    def __init__(self, profile: Optional[CameraProfile] = None):
        self.profile = profile or CameraProfile.default_profile()

    def set_profile(self, profile: CameraProfile):
        self.profile = profile

    def infer_context(self, active_tracks_count: int, avg_velocity: float) -> Dict[str, Any]:
        if active_tracks_count >= 25:
            inferred_density = 'EXTREME'
        elif active_tracks_count >= 12:
            inferred_density = 'DENSE'
        elif active_tracks_count >= 4:
            inferred_density = 'MEDIUM'
        else:
            inferred_density = 'SPARSE'

        return {
            'camera_id': self.profile.camera_id,
            'scene_type': self.profile.scene_type,
            'density_category': inferred_density,
            'expected_flow': self.profile.expected_flow,
            'camera_motion': self.profile.camera_motion_type,
            'perspective_scale': self.profile.perspective_scale_factor
        }
