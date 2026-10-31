from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="operator")  # administrator, supervisor, operator

class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, index=True)
    path = Column(String)
    status = Column(String, default="pending")  # pending, processing, completed, error
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("Event", back_populates="video", foreign_keys="Event.video_id")
    tracks = relationship("Track", back_populates="video")

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True)
    stream_url = Column(String, unique=True, index=True)
    stream_type = Column(String, default="mjpeg")  # mjpeg, rtsp
    status = Column(String, default="online")      # online, offline
    is_analysis_running = Column(Boolean, default=False)
    
    # Camera Profile & Settings
    scene_type = Column(String, default="Mall")     # Mall, Airport, Office, Parking, Classroom, Mosque, Hospital, Road
    sensitivity = Column(String, default="Medium")  # Low, Medium, High
    model_profile = Column(String, default="yolov8n.pt") # yolov8n.pt (Indoor/Fast), yolov8m.pt (Outdoor/Accurate)
    replay_length = Column(Integer, default=15)    # Duration of sliced evidence clips
    rules_enabled = Column(JSON, nullable=True)     # List of enabled plugin names e.g., ["violence", "theft"]
    
    # Calibration Coefficients
    calibration = Column(JSON, nullable=True)       # {"height_m": 3.0, "angle_deg": 45, "fov_deg": 90, "ppm": 50, "perspective_matrix": []}
    
    # Interactive Zone Overlays
    zones = Column(JSON, nullable=True)             # List of drawn zones: [{"id": 1, "name": "Entrance", "type": "Restricted", "points": [[x1, y1], ...]}]

    events = relationship("Event", back_populates="camera")

class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    track_id = Column(Integer, index=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    object_class = Column(Integer)
    trajectory = Column(JSON)
    velocity = Column(Float)

    video = relationship("Video", back_populates="tracks")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    type = Column(String, index=True)  # violence, theft, accident, etc.
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    confidence = Column(Float)
    involved_track_ids = Column(JSON)
    severity = Column(String, default="high")  # low, medium, high, critical
    status = Column(String, default="unread")  # unread, read, acknowledged, resolved, archived
    
    # Enterprise Hardening & Source Scoping Fields
    source_type = Column(String, default="LIVE_CAMERA")  # LIVE_CAMERA | UPLOADED_VIDEO | SYSTEM
    source_id = Column(String, nullable=True)             # camera_id string or job_id string
    job_id = Column(String, ForeignKey("videos.id"), nullable=True)
    trace_id = Column(String, nullable=True)
    reason_codes = Column(JSON, nullable=True)
    
    escalation_stage = Column(String, default="Suspicious") # Suspicious, Possible, Likely, Confirmed
    risk_score = Column(Float, default=0.0)                 # Calculated score from 0.0 to 100.0
    risk_rating = Column(String, default="LOW")             # LOW, MEDIUM, HIGH, CRITICAL
    explainability = Column(JSON, nullable=True)            # Explainable decision tree paths & confidence splits
    operator_feedback = Column(String, nullable=True)       # "Confirmed" or "False Alarm" (Active Learning)
    case_id = Column(Integer, ForeignKey("investigation_cases.id"), nullable=True)

    video = relationship("Video", back_populates="events", foreign_keys=[video_id])
    camera = relationship("Camera", back_populates="events")
    alerts = relationship("Alert", back_populates="event")
    snapshots = relationship("Snapshot", back_populates="event")
    clips = relationship("VideoClip", back_populates="event")
    case = relationship("InvestigationCase", back_populates="events")

class InvestigationCase(Base):
    __tablename__ = "investigation_cases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    status = Column(String, default="open")        # open, investigating, resolved, closed
    assigned_operator = Column(String, nullable=True)
    resolution_notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    events = relationship("Event", back_populates="case")

class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_key = Column(String, index=True)
    rule_value = Column(String)
    version_number = Column(Integer, default=1)
    updated_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    severity = Column(String, default="high")
    status = Column(String, default="unread")
    acknowledged = Column(Boolean, default=False)
    seen = Column(Boolean, default=False)
    played_sound = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="alerts")

class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)  # Serialized threshold settings
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    image_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="snapshots")

class VideoClip(Base):
    __tablename__ = "video_clips"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    clip_path = Column(String)
    duration = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="clips")

class HealthLog(Base):
    __tablename__ = "health_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    service_name = Column(String, index=True)  # backend, ai_worker, redis, db
    status = Column(String)  # healthy, warning, degraded
    metrics = Column(JSON)  # CPU, RAM, Latency details, VRAM, container status
    created_at = Column(DateTime, default=datetime.utcnow)

class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    fps = Column(Float)
    latency_ms = Column(Float)
    cpu_usage = Column(Float)
    ram_usage = Column(Float)
    gpu_usage = Column(Float, nullable=True)
    vram_usage = Column(Float, nullable=True)
    dropped_frames = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, index=True)
    action = Column(String)
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    channel = Column(String)  # desktop, email, webhook, sms
    status = Column(String, default="pending")  # pending, sent, failed
    sent_at = Column(DateTime, nullable=True)
