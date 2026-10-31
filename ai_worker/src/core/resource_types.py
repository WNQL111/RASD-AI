import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class GpuHealthState:
    GPU_HEALTHY = "GPU_HEALTHY"
    GPU_BUSY = "GPU_BUSY"
    GPU_PRESSURED = "GPU_PRESSURED"
    GPU_CRITICAL = "GPU_CRITICAL"
    GPU_UNAVAILABLE = "GPU_UNAVAILABLE"

class TaskPriority:
    CRITICAL_EVENT = 100
    HIGH_RISK_INTERACTION = 80
    EVENT_CANDIDATE = 70
    TRACK_RECOVERY = 60
    POSE_REQUIRED = 50
    BALANCED_DETECTION = 40
    FAST_DETECTION = 30
    BACKGROUND_WORK = 10

class QualityLevel:
    L0_CHEAP_SCENE = "L0_CHEAP_SCENE"
    L1_FAST_DETECTOR = "L1_FAST_DETECTOR"
    L2_BALANCED_DETECTOR = "L2_BALANCED_DETECTOR"
    L3_SELECTIVE_POSE = "L3_SELECTIVE_POSE"
    L4_DEEP_ROI_ANALYSIS = "L4_DEEP_ROI_ANALYSIS"
    L5_CRITICAL_EVIDENCE = "L5_CRITICAL_EVIDENCE"

@dataclass
class ResourceState:
    gpu_utilization: float = 0.0
    gpu_memory_ratio: float = 0.0
    gpu_health: str = GpuHealthState.GPU_HEALTHY
    queue_depth: int = 0
    frame_backlog: int = 0
    processing_latency_ms: float = 0.0
    dropped_frames_count: int = 0
    active_tasks_count: int = 0
    measured_vram_mb: float = 0.0
    source: str = "MEASURED"
    last_updated: float = field(default_factory=time.time)

@dataclass
class FrameIngressItem:
    frame_id: int
    camera_id: str
    timestamp: float
    frame_data: Any
    age_ms: float = 0.0
    is_critical_evidence: bool = False
