# Violence Domain Data Models & DTO Contracts
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class ViolenceEvidence:
    velocity_evidence: float
    acceleration_evidence: float
    iou_overlap: float
    pose_evidence: float
    negative_evidence_discount: float
    fused_confidence: float

@dataclass
class ViolenceDecision:
    state: str
    confidence: float
    affected_tracks: List[int]
    reason_codes: List[str]
