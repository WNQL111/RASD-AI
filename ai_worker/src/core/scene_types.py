import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class ResolutionClass:
    LOW = "LOW"        # < 720p
    MEDIUM = "MEDIUM"  # 720p - 1080p
    HIGH = "HIGH"      # > 1080p

class FpsClass:
    LOW = "LOW"        # < 15 FPS
    MEDIUM = "MEDIUM"  # 15 - 30 FPS
    HIGH = "HIGH"      # > 30 FPS

class DistanceClass:
    VERY_NEAR = "VERY_NEAR"
    NEAR = "NEAR"
    MEDIUM = "MEDIUM"
    FAR = "FAR"
    VERY_FAR = "VERY_FAR"

class CameraMotionClass:
    STATIC = "STATIC"
    PAN = "PAN"
    TILT = "TILT"
    SHAKE = "SHAKE"
    ZOOM = "ZOOM"
    UNKNOWN = "UNKNOWN"

class AnalysisMode:
    LIGHT = "LIGHT"
    STANDARD = "STANDARD"
    FOCUSED = "FOCUSED"
    DEEP = "DEEP"
    CRITICAL = "CRITICAL"

class SceneState:
    STABLE = "STABLE"
    ACTIVE = "ACTIVE"
    CROWDED = "CROWDED"
    SUSPICIOUS = "SUSPICIOUS"
    HIGH_RISK = "HIGH_RISK"
    EVENT_CANDIDATE = "EVENT_CANDIDATE"
    EVENT_CONFIRMED = "EVENT_CONFIRMED"
    COOLDOWN = "COOLDOWN"

@dataclass
class FrameQuality:
    brightness: float = 128.0
    contrast: float = 50.0
    blur_score: float = 100.0  # Laplacian variance (>100 is sharp)
    noise_estimate: float = 5.0
    illumination_level: str = "NORMAL" # POOR, NORMAL, BRIGHT

@dataclass
class CameraProfile:
    resolution_class: str = ResolutionClass.MEDIUM
    fps_class: str = FpsClass.MEDIUM
    camera_motion_class: str = CameraMotionClass.STATIC
    scene_scale: str = "WIDE"
    apparent_person_scale: str = DistanceClass.MEDIUM
    quality_rating: str = "GOOD"
    confidence: float = 0.9

@dataclass
class MotionFeatures:
    displacement_px: float = 0.0
    apparent_velocity: float = 0.0
    normalized_velocity: float = 0.0
    normalized_acceleration: float = 0.0
    direction_rad: float = 0.0
    angular_change_rad: float = 0.0
    motion_persistence: float = 0.0
    global_motion_vector: List[float] = field(default_factory=lambda: [0.0, 0.0])
    is_camera_motion_compensated: bool = False

@dataclass
class TrackContext:
    track_id: int
    class_id: int = 0
    age: int = 1
    last_seen_frame: int = 0
    bbox: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    center: List[float] = field(default_factory=lambda: [0.0, 0.0])
    motion_features: MotionFeatures = field(default_factory=MotionFeatures)
    distance_class: str = DistanceClass.MEDIUM
    occlusion_level: float = 0.0
    risk_score: float = 0.0
    interaction_candidate_ids: List[int] = field(default_factory=list)

@dataclass
class SceneProfile:
    frame_quality: FrameQuality = field(default_factory=FrameQuality)
    camera_profile: CameraProfile = field(default_factory=CameraProfile)
    people_count: int = 0
    tracked_object_count: int = 0
    crowd_density: float = 0.0
    avg_person_scale: float = 0.0
    interaction_candidates_count: int = 0
    global_motion_class: str = CameraMotionClass.STATIC
    scene_stability: float = 1.0
    motion_level: float = 0.0
    timestamp: float = field(default_factory=time.time)

class CrowdBehaviorState:
    CALM_COHERENT = "CALM_COHERENT"
    NORMAL_FLOW = "NORMAL_FLOW"
    MIXED_FLOW = "MIXED_FLOW"
    DENSE_STABLE = "DENSE_STABLE"
    LOCAL_ANOMALY = "LOCAL_ANOMALY"
    HIGH_RISK_CLUSTER = "HIGH_RISK_CLUSTER"

class CrowdMode:
    NORMAL = "NORMAL"
    CROWD_MODE = "CROWD_MODE"
    EXTREME_CROWD = "EXTREME_CROWD"

class WarmupState:
    WARMUP = "WARMUP"
    BASELINE_ESTABLISHED = "BASELINE_ESTABLISHED"
    NORMAL_MONITORING = "NORMAL_MONITORING"

@dataclass
class CrowdBaselineContext:
    warmup_state: str = WarmupState.WARMUP
    crowd_mode: str = CrowdMode.NORMAL
    behavior_state: str = CrowdBehaviorState.NORMAL_FLOW
    median_speed: float = 0.0
    mad_speed: float = 0.0
    dominant_flow_vector: List[float] = field(default_factory=lambda: [0.0, 0.0])
    flow_coherence: float = 1.0  # 0.0 (chaotic) to 1.0 (perfect parallel flow)
    direction_dispersion: float = 0.0
    active_clusters_count: int = 0
    anomalous_clusters_count: int = 0
    suppression_active: bool = False

@dataclass
class AdaptiveAnalysisProfile:
    mode: str = AnalysisMode.STANDARD
    target_fps: int = 25
    input_resolution: int = 640
    run_pose: bool = False
    run_refinement: bool = False
    roi_enabled: bool = False
    deep_analysis_enabled: bool = False
    reason: str = "baseline_standard_profile"
