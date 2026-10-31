import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class DistanceRelation:
    VERY_FAR = "VERY_FAR"
    FAR = "FAR"
    MEDIUM = "MEDIUM"
    NEAR = "NEAR"
    VERY_NEAR = "VERY_NEAR"
    OVERLAPPING = "OVERLAPPING"

class InteractionState:
    NONE = "NONE"
    PROXIMITY = "PROXIMITY"
    APPROACHING = "APPROACHING"
    SEPARATING = "SEPARATING"
    ACTIVE_INTERACTION = "ACTIVE_INTERACTION"
    SUSPICIOUS_INTERACTION = "SUSPICIOUS_INTERACTION"
    HIGH_RISK_INTERACTION = "HIGH_RISK_INTERACTION"
    EVENT_CANDIDATE = "EVENT_CANDIDATE"
    CONFIRMED_OR_REJECTED = "CONFIRMED_OR_REJECTED"
    COOLDOWN = "COOLDOWN"

@dataclass
class PoseJointFeatures:
    wrist_velocity: float = 0.0
    arm_acceleration: float = 0.0
    torso_asymmetry: float = 0.0
    upper_body_motion: float = 0.0
    pose_confidence: float = 0.0

@dataclass
class InteractionPair:
    track_id_a: int
    track_id_b: int
    distance_class: str = DistanceRelation.MEDIUM
    normalized_distance: float = 1.0
    center_distance_px: float = 100.0
    iou_overlap: float = 0.0
    approach_velocity: float = 0.0  # negative -> approaching, positive -> separating
    approach_score: float = 0.0
    relative_velocity: float = 0.0
    direction_score: float = 0.0    # 1.0 -> converging, -1.0 -> parallel, 0.0 -> crossing
    overlap_score: float = 0.0
    pose_anomaly_score: float = 0.0
    interaction_state: str = InteractionState.NONE
    persistence_frames: int = 1
    risk_score: float = 0.0
    confidence: float = 0.9
    last_updated: float = field(default_factory=time.time)

@dataclass
class InteractionCluster:
    cluster_id: int
    track_ids: List[int] = field(default_factory=list)
    pairs: List[InteractionPair] = field(default_factory=list)
    density: float = 0.0
    motion_energy: float = 0.0
    conflict_score: float = 0.0
    temporal_stability: float = 1.0

@dataclass
class InteractionEngineResult:
    active_pairs: List[InteractionPair] = field(default_factory=list)
    clusters: List[InteractionCluster] = field(default_factory=list)
    max_pair_risk: float = 0.0
    cluster_risk: float = 0.0
    dominant_state: str = InteractionState.NONE
    pose_trigger_needed: bool = False
    explainability_reasons: List[str] = field(default_factory=list)
