from typing import Optional, Dict, Any, List
from .config import CollisionConfig
from .contracts import CollisionState, CollisionDecisionDTO

class CollisionDecisionEngine:
    def __init__(self, config: Optional[CollisionConfig] = None):
        self.config = config or CollisionConfig()

    def process_decision(
        self,
        decision: CollisionDecisionDTO,
        frame_idx: int,
        video_id: str
    ) -> Optional[Dict[str, Any]]:
        if decision.state != CollisionState.CONFIRMED:
            return None

        c1, c2 = decision.pair_key
        event_payload = {
            'event_id': decision.event_id,
            'trace_id': decision.episode_id,
            'source_type': 'UPLOADED_VIDEO' if not video_id.startswith('cam_') else 'RTSP_STREAM',
            'source_id': video_id,
            'job_id': video_id,
            'camera_id': video_id.split('_')[1] if video_id.startswith('cam_') else None,
            'video_id': video_id,
            'type': f'collision_{decision.collision_type.value.lower()}',
            'confidence': float(decision.confidence),
            'involved_track_ids': [int(c1), int(c2)],
            'frame_index': frame_idx,
            'severity': 'high' if decision.confidence >= self.config.HIGH_SEVERITY_THRESHOLD else 'medium',
            'escalation_stage': 'Confirmed',
            'risk_score': float(decision.confidence * 100.0),
            'risk_rating': 'HIGH' if decision.confidence >= self.config.HIGH_SEVERITY_THRESHOLD else 'MEDIUM',
            'reason_codes': decision.reason_codes,
            'explainability': decision.explainability,
            'details': f'Traffic collision incident ({decision.collision_type.value}) detected between Object #{c1} and Object #{c2}'
        }
        return event_payload
