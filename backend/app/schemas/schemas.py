from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "operator"

class UserLogin(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class VideoBase(BaseModel):
    filename: str

class VideoCreate(VideoBase):
    pass

class SnapshotBase(BaseModel):
    event_id: int
    image_path: str

class SnapshotResponse(SnapshotBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class VideoClipBase(BaseModel):
    event_id: int
    clip_path: str
    duration: float

class VideoClipResponse(VideoClipBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class EventBase(BaseModel):
    video_id: Optional[str] = None
    camera_id: Optional[int] = None
    source_type: Optional[str] = "LIVE_CAMERA"
    source_id: Optional[str] = None
    job_id: Optional[str] = None
    trace_id: Optional[str] = None
    type: str
    confidence: float
    involved_track_ids: List[int]
    severity: Optional[str] = "high"
    status: Optional[str] = "unread"
    reason_codes: Optional[List[str]] = []
    
    # SOC Hardening Fields
    escalation_stage: Optional[str] = "Suspicious"
    risk_score: Optional[float] = 0.0
    risk_rating: Optional[str] = "LOW"
    explainability: Optional[Any] = None
    operator_feedback: Optional[str] = None
    case_id: Optional[int] = None

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    snapshots: List[SnapshotResponse] = []
    clips: List[VideoClipResponse] = []

    class Config:
        from_attributes = True

class VideoResponse(VideoBase):
    id: str
    path: str
    status: str
    created_at: datetime
    events: List[EventResponse] = []
    
    class Config:
        from_attributes = True

class AlertBase(BaseModel):
    event_id: int
    severity: str = "high"
    status: str = "unread"
    acknowledged: bool = False
    seen: bool = False
    played_sound: bool = False

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: int
    created_at: datetime
    event: EventResponse
    
    class Config:
        from_attributes = True

class CameraBase(BaseModel):
    name: Optional[str] = None
    stream_url: str
    stream_type: Optional[str] = "mjpeg" # mjpeg, rtsp
    scene_type: Optional[str] = "Mall"
    sensitivity: Optional[str] = "Medium"
    model_profile: Optional[str] = "yolov8n.pt"
    replay_length: Optional[int] = 15
    rules_enabled: Optional[List[str]] = None
    calibration: Optional[Any] = None
    zones: Optional[List[Any]] = None

class CameraCreate(CameraBase):
    pass

class CameraResponse(CameraBase):
    id: int
    name: str
    status: str
    is_analysis_running: bool

    class Config:
        from_attributes = True

class RuleBase(BaseModel):
    key: str
    value: str
    camera_id: Optional[int] = None

class RuleCreate(RuleBase):
    pass

class RuleResponse(RuleBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

class InvestigationCaseBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "open"
    assigned_operator: Optional[str] = None
    resolution_notes: Optional[str] = None

class InvestigationCaseCreate(InvestigationCaseBase):
    event_id: Optional[int] = None
    event_ids: Optional[List[int]] = None

class InvestigationCaseResponse(InvestigationCaseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    events: List[EventResponse] = []

    class Config:
        from_attributes = True

class RuleVersionResponse(BaseModel):
    id: int
    rule_key: str
    rule_value: str
    version_number: int
    updated_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class HealthLogBase(BaseModel):
    service_name: str
    status: str
    metrics: dict

class HealthLogResponse(HealthLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PerformanceMetricBase(BaseModel):
    camera_id: Optional[int] = None
    fps: float
    latency_ms: float
    cpu_usage: float
    ram_usage: float
    gpu_usage: Optional[float] = None
    vram_usage: Optional[float] = None
    dropped_frames: Optional[int] = 0

class PerformanceMetricResponse(PerformanceMetricBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    username: str
    action: str
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True
