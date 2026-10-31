import math
import time
import json
import logging
import uuid
import requests
import cv2
import numpy as np
from collections import deque
from core.frame_decoder import FrameDecoder
from core.frame_queue import FrameQueue
from core.motion_gate import MotionGate
from detectors.yolo_detector import YoloDetector
from tracker.byte_tracker import ByteTracker
from memory.object_memory import ObjectMemory
from engines.ownership_engine import OwnershipEngine
from engines.rule_engine import RuleEngine

# Evidence Engines
from engines.snapshot_engine import SnapshotEngine
from engines.video_clip_engine import VideoClipEngine

# Enterprise SOC Engines
from engines.model_manager import ModelManager
from engines.calibration_engine import CalibrationEngine
from engines.zone_engine import ZoneEngine
from engines.scene_context_engine import SceneContextEngine
from engines.crowd_analysis_engine import CrowdAnalysisEngine
from engines.decision_fusion_engine import DecisionFusionEngine

# 3D Spatio-Temporal Action Verifier
from core.temporal_3d_verifier import CandidateGated3DVerifier

# Scoped Domain Plugins (Violence + Collision + Crowd Dynamics)
from plugins.violence import ViolencePlugin
from plugins.collision import CollisionPlugin
from plugins.crowd import CrowdPlugin

from core.model_router import model_router
from core.routing_types import RoutingContext
from core.scene_profiler import SceneProfiler
from core.adaptive_interaction_engine import AdaptiveInteractionEngine
from core.event_reasoning_orchestrator import EventReasoningOrchestrator
from core.adaptive_compute_orchestrator import AdaptiveComputeOrchestrator

logger = logging.getLogger(__name__)

class AdaptiveExecutionController:
    LEVEL_0 = "LEVEL_0_SCREENING"
    LEVEL_1 = "LEVEL_1_DETECTION"
    LEVEL_2 = "LEVEL_2_INTERACTION"
    LEVEL_3 = "LEVEL_3_FORENSIC"
    LEVEL_4 = "LEVEL_4_EVIDENCE"

    def __init__(self, rule_engine: RuleEngine = None):
        self.rule_engine = rule_engine or RuleEngine()
        self.motion_gate = MotionGate(
            motion_threshold=self.rule_engine.get_float("motion_threshold", 0.003),
            pixel_change_threshold=self.rule_engine.get_float("pixel_change_threshold", 0.005)
        )
        self.current_level = self.LEVEL_0
        self.current_mode = "turbo"
        self.hysteresis_counter = 0

        self.metrics = {
            "total_decoded_frames": 0,
            "screened_frames": 0,
            "yolo_frames": 0,
            "tracker_frames": 0,
            "pose_frames": 0,
            "skipped_frames": 0,
            "skip_ratio": 0.0,
            "yolo_reduction_ratio": 0.0,
            "level_switches": 0,
            "start_time": time.time(),
            "avg_fps": 0.0
        }

    def reset(self):
        self.motion_gate.reset()
        self.current_level = self.LEVEL_0
        self.hysteresis_counter = 0

    def evaluate_frame_level(self, frame, memory: ObjectMemory) -> str:
        self.metrics["total_decoded_frames"] += 1
        has_motion, motion_ratio = self.motion_gate.check_motion(frame)

        active_objs = len(memory.objects) if memory and hasattr(memory, 'objects') else 0
        high_activity = False
        if active_objs > 0:
            for obj in memory.objects.values():
                if getattr(obj, 'velocity', 0.0) >= 6.0 or getattr(obj, 'acceleration', 0.0) >= 10.0:
                    high_activity = True
                    break

        if high_activity or active_objs > 2:
            target_level = self.LEVEL_3
        elif active_objs > 0:
            target_level = self.LEVEL_2
        elif has_motion and motion_ratio >= self.motion_gate.pixel_change_threshold:
            target_level = self.LEVEL_1
        else:
            target_level = self.LEVEL_0

        if target_level > self.current_level:
            self.current_level = target_level
            self.hysteresis_counter = 0
            self.metrics["level_switches"] += 1
        elif target_level < self.current_level:
            # If coming down from Level 1 to Level 0, downgrade immediately
            if self.current_level == self.LEVEL_1 and target_level == self.LEVEL_0:
                self.current_level = self.LEVEL_0
                self.hysteresis_counter = 0
                self.metrics["level_switches"] += 1
            elif self.hysteresis_counter >= 15:
                self.current_level = target_level
                self.hysteresis_counter = 0
                self.metrics["level_switches"] += 1
            else:
                self.hysteresis_counter += 1
        else:
            self.hysteresis_counter = 0

        return self.current_level

    def should_sample_frame(self, frame_idx: int) -> bool:
        if self.current_level in [self.LEVEL_3, self.LEVEL_4]:
            return True
        elif self.current_level == self.LEVEL_2:
            return (frame_idx % 2 == 0)
        elif self.current_level == self.LEVEL_1:
            return (frame_idx % 3 == 0)
        else:
            return (frame_idx % 6 == 0)

class AIPipeline:
    def __init__(self, detector: YoloDetector, redis_client=None, video_path: str = None, fps: float = 25.0):
        self.detector = detector
        self.redis_client = redis_client
        self.video_path = video_path
        self.fps = fps
        
        self.rule_engine = RuleEngine()
        self.memory = ObjectMemory()
        self.ownership_engine = OwnershipEngine()
        self.snapshot_engine = SnapshotEngine()
        self.clip_engine = VideoClipEngine()
        
        self.model_manager = ModelManager()
        self.calibration_engine = CalibrationEngine()
        self.zone_engine = ZoneEngine()
        self.scene_context_engine = SceneContextEngine()
        self.crowd_analysis_engine = CrowdAnalysisEngine()
        self.decision_fusion_engine = DecisionFusionEngine()
        
        self.verifier_3d = CandidateGated3DVerifier()
        self.adaptive_controller = AdaptiveExecutionController(self.rule_engine)

        self.scene_profiler = SceneProfiler()
        self.adaptive_interaction = AdaptiveInteractionEngine()
        self.event_reasoner = EventReasoningOrchestrator()
        self.adaptive_compute = AdaptiveComputeOrchestrator()
        
        self.pose_detector = None
        try:
            from detectors.pose_detector import PoseDetector
            self.pose_detector = PoseDetector(model_dir="./models", model_name="yolov8n-pose.pt")
            logger.info("Pipeline: PoseDetector initialized.")
        except Exception as e:
            logger.warning(f"Pipeline: PoseDetector initialization failed: {e}")

        self.load_rules_from_backend()

        self.plugins = [
            ViolencePlugin(self.rule_engine),
            CollisionPlugin(self.rule_engine),
            CrowdPlugin(self.rule_engine)
        ]
        logger.info("Pipeline initialized strictly with Violence, Collision, and 3D Action Intelligence.")
        self.threats_detected_count = 0

    def load_rules_from_backend(self):
        try:
            backend_url = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8001/api/rules")
            response = requests.get(backend_url, timeout=0.5)
            if response.status_code == 200:
                rules_data = response.json()
                for rule in rules_data:
                    k, v = rule["key"], rule["value"]
                    if k.endswith("_thresh") or k in ["pre_event_roll", "post_event_roll"]:
                        try:
                            self.rule_engine.set(k, float(v))
                        except ValueError:
                            self.rule_engine.set(k, v)
                    else:
                        self.rule_engine.set(k, v)
                logger.info(f"Loaded {len(rules_data)} enterprise rules from Backend.")
        except Exception:
            pass

    def update_rules_from_payload(self, rules_dict: dict):
        for k, v in rules_dict.items():
            self.rule_engine.set(k, v)
        logger.info(f"Pipeline: Dynamically updated {len(rules_dict)} rules.")

    def run_frame(self, frame, frame_idx, video_id, tracker: ByteTracker, stream_id: str = None):
        return self.process_frame(frame, frame_idx, video_id, tracker)

    def process_frame(self, frame, frame_idx, video_id, tracker: ByteTracker):
        timeline_sec = float(frame_idx) / float(self.fps) if self.fps > 0 else 0.0

        if self.verifier_3d:
            self.verifier_3d.record_frame(
                stream_id=video_id,
                frame_idx=frame_idx,
                frame=frame,
                timestamp_sec=timeline_sec
            )

        level = self.adaptive_controller.evaluate_frame_level(frame, self.memory)

        routing_ctx = RoutingContext(
            current_level=level,
            scene_state="NORMAL",
            risk_state="LOW",
            pose_needed=(level in [AdaptiveExecutionController.LEVEL_3, AdaptiveExecutionController.LEVEL_4]),
            latency_ms=10.0,
            gpu_memory_total_mb=4096.0
        )
        model_decision = model_router.select_model(routing_ctx)

        if level == AdaptiveExecutionController.LEVEL_0:
            self.adaptive_controller.metrics["screened_frames"] += 1
            return []

        should_sample = self.adaptive_controller.should_sample_frame(frame_idx)
        if should_sample:
            self.adaptive_controller.metrics["yolo_frames"] += 1
            # ByteTracker runs detection & tracking in a single optimized pass
            tracked_objects = tracker.update(frame)
        else:
            self.adaptive_controller.metrics["skipped_frames"] += 1
            tracked_objects = []

        self.memory.update_frame(tracked_objects, frame_idx)

        pose_data_map = {}
        # Gate pose estimation strictly to highest threat levels and small focused scenes
        if level == AdaptiveExecutionController.LEVEL_4 and self.pose_detector and len(tracked_objects) <= 3:
            self.adaptive_controller.metrics["pose_frames"] += 1
            for obj in tracked_objects:
                if obj["class_id"] == 0:
                    x1, y1, x2, y2 = map(int, obj["bbox"])
                    h, w = frame.shape[:2]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    if (x2 - x1) > 20 and (y2 - y1) > 40:
                        crop = frame[y1:y2, x1:x2]
                        poses = self.pose_detector.detect(crop)
                        if poses:
                            pose_data_map[obj["track_id"]] = poses[0]

        crowd_density = self.crowd_analysis_engine.calculate_density(tracked_objects, frame.shape)
        crowd_coherence = self.crowd_analysis_engine.calculate_motion_coherence(self.memory)
        crowd_features = {
            "density": crowd_density,
            "coherence": crowd_coherence,
            "people_count": len([o for o in tracked_objects if o["class_id"] == 0])
        }

        fused_events = []
        for plugin in self.plugins:
            try:
                events = plugin.analyze(
                    self.memory, 
                    frame_idx=frame_idx, 
                    video_id=video_id, 
                    crowd_features=crowd_features,
                    pose_data_map=pose_data_map,
                    verifier_3d=self.verifier_3d
                )
                if events:
                    fused_events.extend(events)
            except TypeError:
                try:
                    events = plugin.analyze(self.memory, frame_idx=frame_idx, video_id=video_id)
                    if events:
                        fused_events.extend(events)
                except Exception as pl_err:
                    logger.error(f"Plugin {plugin.__class__.__name__} execution error: {pl_err}")

        for event in fused_events:
            event_uuid = str(uuid.uuid4())
            event["id"] = event_uuid
            event["timestamp"] = time.time()
            event["source_type"] = "LIVE_CAMERA" if str(video_id).startswith("cam_") else "UPLOADED_VIDEO"
            event["source_id"] = str(video_id)
            event["video_id"] = None if str(video_id).startswith("cam_") else str(video_id)
            event["camera_id"] = int(str(video_id).replace("cam_", "")) if str(video_id).startswith("cam_") else None
            
            # Save Snapshot
            try:
                snapshot_url = self.snapshot_engine.save_snapshot(
                    frame=frame,
                    event_id=event_uuid,
                    involved_tracks=event.get("involved_tracks", []),
                    memory=self.memory
                )
                event["snapshot_path"] = snapshot_url
            except Exception as e:
                logger.error(f"Failed to generate snapshot: {e}")
                event["snapshot_path"] = None

            # Video Clip Roll
            if self.video_path and not video_id.startswith("cam_"):
                pre_sec = self.rule_engine.get_float("pre_event_roll", 5.0)
                post_sec = self.rule_engine.get_float("post_event_roll", 10.0)
                clip_url = self.clip_engine.create_clip_from_video(
                    source_path=self.video_path,
                    event_id=event_uuid,
                    event_frame=frame_idx,
                    fps=self.fps,
                    pre_sec=pre_sec,
                    post_sec=post_sec
                )
                event["clip_path"] = clip_url
                event["clip_duration"] = pre_sec + post_sec

            event["timestamp_sec"] = round(timeline_sec, 2)
            event["frame_index"] = frame_idx
            event["timeline_sec"] = round(timeline_sec, 2)
            min_part = int(timeline_sec // 60)
            sec_part = int(timeline_sec % 60)
            formatted_offset = f"{min_part:02d}:{sec_part:02d}"
            event["formatted_offset"] = formatted_offset
            
            if "explainability" not in event or not isinstance(event["explainability"], dict):
                event["explainability"] = {}
            event["explainability"]["timestamp_sec"] = round(timeline_sec, 2)
            event["explainability"]["frame_index"] = frame_idx
            event["explainability"]["formatted_offset"] = formatted_offset
            event["explainability"]["exact_time_str"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            event["verification_status"] = "LOCAL_VERIFIED"
            event["escalation_stage"] = "Confirmed"

            self.publish_event(event)

        if str(video_id).startswith("cam_"):
            try:
                annotated = frame.copy()
                for obj in tracked_objects:
                    x1, y1, x2, y2 = map(int, obj["bbox"])
                    track_id = obj["track_id"]
                    cls_id = obj["class_id"]
                    label = f"Person #{track_id}" if cls_id == 0 else f"Vehicle #{track_id}"
                    color = (0, 255, 0) if cls_id == 0 else (255, 128, 0)
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

                _, jpeg_buf = cv2.imencode('.jpg', annotated)
                if self.redis_client:
                    cam_id = video_id.split("_")[1]
                    self.redis_client.setex(f"camera:{cam_id}:latest_frame", 3, jpeg_buf.tobytes())
            except Exception as e:
                logger.error(f"Pipeline: Failed to annotate stream frame: {e}")

        return fused_events

    def publish_event(self, event):
        self.threats_detected_count += 1
        event["event_stage"] = "THREAT_CONFIRMED"
        event["event_kind"] = "EVENT_RESULT"
        logger.info(f"🚨 EVENT CONFIRMED (#{self.threats_detected_count}): {event.get('type')}")
        if self.redis_client:
            try:
                def default_json_serializer(o):
                    if isinstance(o, (np.bool_, np.generic)):
                        return bool(o) if isinstance(o, np.bool_) else float(o)
                    return str(o)
                self.redis_client.publish("asis_events_channel", json.dumps(event, default=default_json_serializer))
            except Exception as e:
                logger.error(f"Failed to publish event to Redis: {e}")

Pipeline = AIPipeline
