from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field

class CollisionType(str, Enum):
    VEHICLE_VEHICLE = 'VEHICLE_VEHICLE'
    VEHICLE_PEDESTRIAN = 'VEHICLE_PEDESTRIAN'
    PEDESTRIAN_VEHICLE = 'PEDESTRIAN_VEHICLE'
    VEHICLE_OBJECT = 'VEHICLE_OBJECT'
    UNKNOWN = 'UNKNOWN'

class CollisionState(str, Enum):
    MONITORING = 'MONITORING'
    CANDIDATE = 'CANDIDATE'
    INVESTIGATING = 'INVESTIGATING'
    SUPPORTED = 'SUPPORTED'
    CONFIRMED = 'CONFIRMED'
    CLOSED = 'CLOSED'
    REJECTED = 'REJECTED'

class CollisionCandidateDTO(BaseModel):
    pair_key: Tuple[int, int]
    collision_type: CollisionType
    track_id_1: int = 0
    track_id_2: int = 0
    class_id_1: int = 2
    class_id_2: int = 2
    spatial_distance: float = 0.0
    ground_distance: float = 0.0
    iou_overlap: float = 0.0
    relative_speed: float = 0.0
    approach_rate: float = 0.0
    cosine_similarity: float = 1.0
    timestamp: float = 0.0

class CollisionEvidenceDTO(BaseModel):
    pair_key: Tuple[int, int]
    collision_type: CollisionType
    base_score: float = 0.0
    approach_evidence: float = 0.0
    overlap_evidence: float = 0.0
    deceleration_evidence: float = 0.0
    deviation_evidence: float = 0.0
    post_impact_evidence: float = 0.0
    track_reliability_score: float = 1.0
    suppression_discount: float = 0.0
    final_confidence: float = 0.0
    evidence_score: float = 0.0
    score_3d: float = 0.0
    quality: str = 'HIGH'
    reason_codes: List[str] = Field(default_factory=list)
    explainability: Dict[str, Any] = Field(default_factory=dict)

class CollisionDecisionDTO(BaseModel):
    pair_key: Tuple[int, int]
    collision_type: CollisionType
    state: CollisionState
    confidence: float
    persistence_count: int
    episode_id: Optional[str] = None
    event_id: Optional[str] = None
    reason_codes: List[str] = Field(default_factory=list)
    explainability: Dict[str, Any] = Field(default_factory=dict)
