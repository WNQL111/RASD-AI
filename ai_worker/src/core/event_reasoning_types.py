import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class FirewallDecision:
    PASS = "PASS"
    SUPPRESS = "SUPPRESS"
    HOLD = "HOLD"
    REQUIRE_MORE_EVIDENCE = "REQUIRE_MORE_EVIDENCE"

class EventLifecycleState:
    NONE = "NONE"
    SUSPECTED = "SUSPECTED"
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    ENDING = "ENDING"
    ENDED = "ENDED"
    COOLDOWN = "COOLDOWN"
    REJECTED = "REJECTED"

@dataclass
class EventEvidenceVector:
    spatial_score: float = 0.0
    motion_score: float = 0.0
    relative_motion_score: float = 0.0
    interaction_score: float = 0.0
    pose_score: float = 0.0
    joint_score: float = 0.0
    persistence_score: float = 0.0
    contradictory_score: float = 0.0
    net_evidence_score: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "spatial": self.spatial_score,
            "motion": self.motion_score,
            "relative_motion": self.relative_motion_score,
            "interaction": self.interaction_score,
            "pose": self.pose_score,
            "joint": self.joint_score,
            "persistence": self.persistence_score,
            "contradiction": self.contradictory_score,
            "net_evidence": self.net_evidence_score
        }

@dataclass
class EventParticipants:
    track_ids: List[int] = field(default_factory=list)
    primary_track_a: int = 0
    primary_track_b: int = 0
    participant_count: int = 0

@dataclass
class EventReasoningState:
    event_id: str
    event_type: str = "security_anomaly"
    participants: EventParticipants = field(default_factory=EventParticipants)
    current_lifecycle_state: str = EventLifecycleState.NONE
    evidence_vector: EventEvidenceVector = field(default_factory=EventEvidenceVector)
    firewall_decision: str = FirewallDecision.PASS
    explainability_reasons: List[str] = field(default_factory=list)
    start_frame: int = 0
    last_seen_frame: int = 0
    cooldown_frames_remaining: int = 0
    last_updated: float = field(default_factory=time.time)
