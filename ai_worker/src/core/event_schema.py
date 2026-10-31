import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

class EventTypes:
    VIOLENCE_CANDIDATE = "VIOLENCE_CANDIDATE"
    VIOLENCE_CONFIRMED = "VIOLENCE_CONFIRMED"
    VIOLENCE_ENDED = "VIOLENCE_ENDED"

    THEFT_CANDIDATE = "THEFT_CANDIDATE"
    THEFT_CONFIRMED = "THEFT_CONFIRMED"
    THEFT_ENDED = "THEFT_ENDED"

    COLLISION_CANDIDATE = "COLLISION_CANDIDATE"
    COLLISION_CONFIRMED = "COLLISION_CONFIRMED"
    COLLISION_ENDED = "COLLISION_ENDED"

    PROGRESS_UPDATE = "progress_update"
    ANALYSIS_COMPLETE = "analysis_complete"
    ANALYSIS_FAILED = "analysis_failed"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"

@dataclass
class EventEnvelope:
    """
    Standardized, Versioned, Idempotent AI Event Contract Schema for ASIS-V2.
    Shared contract across AI Worker, Redis Event Bus, Backend, API, and Frontend.
    Enforces strict source scoping (LIVE_CAMERA vs UPLOADED_VIDEO) and job isolation.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = EventTypes.VIOLENCE_CANDIDATE
    event_version: str = "1.0"
    source_type: str = "LIVE_CAMERA"  # "LIVE_CAMERA" | "UPLOADED_VIDEO" | "SYSTEM"
    source_id: Optional[str] = None   # camera_id string or job_id string
    job_id: Optional[str] = None      # Explicit Video Analysis Job ID
    camera_id: Optional[str] = None   # Explicit Camera ID
    video_id: Optional[str] = None    # Video ID alias for backwards compatibility
    timestamp: float = field(default_factory=time.time)
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sequence: int = 1
    severity: str = "HIGH"
    confidence: float = 0.90
    risk_score: float = 0.0
    status: str = "unread"             # "unread" | "read" | "acknowledged" | "resolved"
    escalation_stage: str = "CANDIDATE"
    participants: List[int] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    snapshot_reference: Optional[str] = None
    clip_reference: Optional[str] = None
    telemetry: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
