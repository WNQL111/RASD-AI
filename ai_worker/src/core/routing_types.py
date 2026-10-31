import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class ModelTask:
    PERSON_DETECTION = "person_detection"
    OBJECT_DETECTION = "object_detection"
    POSE_ESTIMATION = "pose_estimation"
    ACTION_RECOGNITION = "action_recognition"

class ModelTier:
    FAST = "FAST"
    BALANCED = "BALANCED"
    HIGH_ACCURACY = "HIGH_ACCURACY"
    SPECIALIST = "SPECIALIST"

class ModelStatus:
    REGISTERED = "REGISTERED"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    LOADING = "LOADING"
    READY = "READY"
    FAILED = "FAILED"

class LatencyStatus:
    ESTIMATED = "ESTIMATED"
    MEASURED = "MEASURED"
    UNKNOWN = "UNKNOWN"

@dataclass
class ModelSpec:
    model_id: str
    path: str
    task: str
    tier: str
    supported_tasks: List[str] = field(default_factory=list)
    estimated_vram_mb: float = 350.0
    expected_latency_ms: float = 10.0
    latency_status: str = LatencyStatus.ESTIMATED
    status: str = ModelStatus.REGISTERED
    load_error: Optional[str] = None
    last_load_time: float = 0.0
    last_failure_time: float = 0.0
    priority: int = 10

@dataclass
class RoutingContext:
    scene_state: str = "NORMAL"
    risk_state: str = "LOW"
    current_level: str = "LEVEL_0_SCREENING"
    source_fps: float = 25.0
    processing_fps: float = 25.0
    frame_width: int = 1920
    frame_height: int = 1080
    people_count: int = 0
    track_count: int = 0
    interaction_count: int = 0
    interaction_candidate_count: int = 0
    suspicious_count: int = 0
    motion_score: float = 0.0
    normalized_motion: float = 0.0
    crowd_density: float = 0.0
    camera_motion: str = "STATIC"
    evidence_score: float = 0.0
    analysis_pressure: float = 0.0
    queue_depth: int = 0
    gpu_utilization: float = 0.0
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 4096.0
    cpu_utilization: float = 0.0
    latency_ms: float = 0.0
    camera_profile: str = "default"
    pose_needed: bool = False
    refinement_needed: bool = False

@dataclass
class RoutingDecision:
    selected_model: str
    task: str
    tier: str
    reason: str
    confidence: float = 1.0
    fallback_model: str = "yolov8n.pt"
    target_fps: int = 25
    image_size: int = 640
    run_pose: bool = False
    run_refinement: bool = False
    priority: int = 10
    decision_timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_model": self.selected_model,
            "task": self.task,
            "tier": self.tier,
            "reason": self.reason,
            "confidence": self.confidence,
            "fallback_model": self.fallback_model,
            "target_fps": self.target_fps,
            "image_size": self.image_size,
            "run_pose": self.run_pose,
            "run_refinement": self.run_refinement,
            "priority": self.priority,
            "decision_timestamp": self.decision_timestamp
        }
