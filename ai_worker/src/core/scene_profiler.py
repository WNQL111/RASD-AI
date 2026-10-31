import cv2
import numpy as np
import math
import logging
import time
from typing import List, Dict, Tuple, Optional, Any
from core.scene_types import (
    FrameQuality, CameraProfile, MotionFeatures, TrackContext, SceneProfile,
    AdaptiveAnalysisProfile, ResolutionClass, FpsClass, DistanceClass,
    CameraMotionClass, SceneState, AnalysisMode
)
from core.camera_motion_compensation import CameraMotionAnalyzer
from core.normalized_motion_engine import NormalizedMotionEngine
from core.temporal_context_engine import TemporalContextManager
from core.evidence_engine import EvidenceEngine
from core.scene_state_machine import SceneStateMachine
from core.crowd_baseline_engine import CrowdBaselineEngine
from core.global_crowd_flow_engine import GlobalCrowdFlowEngine
from core.spatial_partitioning_engine import SpatialPartitioningEngine
from core.local_behavioral_anomaly_engine import LocalBehavioralAnomalyEngine
from core.suppression_evidence_engine import SuppressionEvidenceEngine

logger = logging.getLogger(__name__)

class SceneProfiler:
    """
    Independent Scene Intelligence Profiler for ASIS-V2.
    Extracts frame quality, auto-characterizes camera profile, normalizes motion,
    tracks temporal context, computes crowd baseline, flow coherence, spatial partitioning,
    local behavioral anomalies, suppression evidence, and evaluates SceneStateMachine.
    Does NOT invoke models directly (delegates decision to ModelRouter).
    """
    def __init__(self, fps: float = 25.0):
        self.fps = fps
        self.camera_motion_analyzer = CameraMotionAnalyzer()
        self.normalized_motion_engine = NormalizedMotionEngine(baseline_fps=fps)
        self.temporal_context_manager = TemporalContextManager()
        self.evidence_engine = EvidenceEngine()
        self.scene_state_machine = SceneStateMachine()
        self.crowd_baseline_engine = CrowdBaselineEngine()
        self.global_flow_engine = GlobalCrowdFlowEngine()
        self.spatial_partitioning_engine = SpatialPartitioningEngine()
        self.local_anomaly_engine = LocalBehavioralAnomalyEngine()
        self.suppression_engine = SuppressionEvidenceEngine()

    def analyze_frame_quality(self, frame: np.ndarray) -> FrameQuality:
        """
        Calculates brightness, contrast, blur score (Laplacian var), and noise estimate.
        Execution budget: < 0.5ms on CPU downsampled gray image.
        """
        if frame is None:
            return FrameQuality()

        try:
            h, w = frame.shape[:2]
            target_w = 320
            scale = target_w / float(w) if w > target_w else 1.0
            if scale < 1.0:
                small = cv2.resize(frame, (target_w, int(h * scale)), interpolation=cv2.INTER_NEAREST)
            else:
                small = frame

            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if len(small.shape) == 3 else small

            mean_val, std_val = cv2.meanStdDev(gray)
            brightness = float(mean_val[0][0])
            contrast = float(std_val[0][0])

            # Blur score via Laplacian variance
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            # Illumination categorization
            illum = "NORMAL"
            if brightness < 40.0:
                illum = "POOR"
            elif brightness > 210.0:
                illum = "BRIGHT"

            return FrameQuality(
                brightness=round(brightness, 1),
                contrast=round(contrast, 1),
                blur_score=round(blur_score, 1),
                noise_estimate=round(max(0.0, 300.0 - blur_score) / 30.0, 1),
                illumination_level=illum
            )
        except Exception as e:
            logger.warning(f"SceneProfiler: Frame quality analysis error ({e})")
            return FrameQuality()

    def classify_distance(self, bbox: List[float], frame_w: int, frame_h: int) -> str:
        """
        Classifies apparent object distance based on normalized bounding box area.
        """
        x1, y1, x2, y2 = bbox
        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)
        frame_area = max(1.0, frame_w * frame_h)
        norm_area = (bw * bh) / float(frame_area)

        if norm_area < 0.003:
            return DistanceClass.VERY_FAR
        elif norm_area < 0.015:
            return DistanceClass.FAR
        elif norm_area < 0.060:
            return DistanceClass.MEDIUM
        elif norm_area < 0.180:
            return DistanceClass.NEAR
        else:
            return DistanceClass.VERY_NEAR

    def analyze_crowd_and_interactions(
        self,
        tracks: List[TrackContext],
        frame_w: int = 1280,
        frame_h: int = 720,
        proximity_thresh_px: float = 120.0
    ) -> Tuple[float, int, List[Tuple[int, int]]]:
        """
        Calculates spatial crowd density and detects interaction candidates.
        Uses area occupancy and spatial proximity to prevent single-digit crowds from hitting max density.
        """
        n = len(tracks)
        if n <= 1:
            return 0.0, 0, []

        persons = [t for t in tracks if t.class_id == 0]
        p_count = len(persons)
        if p_count <= 1:
            return 0.0, 0, []

        interaction_pairs = []
        interaction_count = 0

        # Calculate bounding box total spatial coverage area ratio
        frame_area = max(1.0, frame_w * frame_h)
        total_bbox_area = 0.0
        for p in persons:
            bw = max(1.0, p.bbox[2] - p.bbox[0])
            bh = max(1.0, p.bbox[3] - p.bbox[1])
            total_bbox_area += bw * bh

        area_occupancy_ratio = min(1.0, total_bbox_area / (frame_area * 0.4))

        # Pairwise interaction check (bounded to top 20 active tracks)
        bounded_persons = persons[:20]
        m = len(bounded_persons)

        for i in range(m):
            c1 = bounded_persons[i].center
            for j in range(i + 1, m):
                c2 = bounded_persons[j].center
                dist = math.hypot(c1[0] - c2[0], c1[1] - c2[1])

                if dist <= proximity_thresh_px:
                    interaction_count += 1
                    interaction_pairs.append((bounded_persons[i].track_id, bounded_persons[j].track_id))
                    bounded_persons[i].interaction_candidate_ids.append(bounded_persons[j].track_id)
                    bounded_persons[j].interaction_candidate_ids.append(bounded_persons[i].track_id)

        # Scale crowd density continuously based on area occupancy ratio & count
        crowd_density = round(min(1.0, (area_occupancy_ratio * 0.6) + min(0.4, p_count / 50.0)), 3)
        return crowd_density, interaction_count, interaction_pairs

    def profile_scene(
        self,
        frame: np.ndarray,
        raw_tracked_objects: List[Any],
        frame_idx: int
    ) -> Tuple[SceneProfile, AdaptiveAnalysisProfile]:
        """
        Main entry point: Analyzes frame, tracks, motion, quality, and scene state.
        Returns complete (SceneProfile, AdaptiveAnalysisProfile).
        """
        h, w = (frame.shape[:2]) if frame is not None else (1080, 1920)

        # 1. Analyze Quality & Camera Motion
        quality = self.analyze_frame_quality(frame)
        global_vector, camera_motion_class = self.camera_motion_analyzer.analyze_frame_motion(frame)

        # 2. Update Temporal Tracks & Compute Normalized Motion
        active_tracks: List[TrackContext] = []
        max_norm_vel = 0.0

        for obj in raw_tracked_objects:
            tid = getattr(obj, "track_id", getattr(obj, "id", 0))
            cid = getattr(obj, "class_id", getattr(obj, "category_id", 0))
            bbox = getattr(obj, "bbox", getattr(obj, "rect", [0.0, 0.0, 0.0, 0.0]))
            raw_dx = getattr(obj, "dx", 0.0)
            raw_dy = getattr(obj, "dy", 0.0)

            dist_class = self.classify_distance(bbox, w, h)

            # Compute scale-normalized motion
            prev_ctx = self.temporal_context_manager.get_track_context(tid)
            prev_vel = prev_ctx.motion_features.normalized_velocity if prev_ctx else 0.0
            dt = (frame_idx - prev_ctx.last_seen_frame) if prev_ctx else 1

            motion_feats = self.normalized_motion_engine.compute_normalized_features(
                raw_dx=raw_dx,
                raw_dy=raw_dy,
                global_dx=global_vector[0],
                global_dy=global_vector[1],
                bbox=bbox,
                frame_w=w,
                frame_h=h,
                prev_velocity=prev_vel,
                dt_frames=dt
            )

            if motion_feats.normalized_velocity > max_norm_vel:
                max_norm_vel = motion_feats.normalized_velocity

            ctx = self.temporal_context_manager.update_track(
                track_id=tid,
                class_id=cid,
                frame_idx=frame_idx,
                bbox=bbox,
                motion_features=motion_feats,
                distance_class=dist_class
            )
            active_tracks.append(ctx)

        # Prune missing tracks
        self.temporal_context_manager.prune_stale_tracks(frame_idx)

        # 3. Analyze Crowd Density & Interactions
        crowd_density, interaction_count, interaction_pairs = self.analyze_crowd_and_interactions(
            active_tracks, frame_w=w, frame_h=h
        )

        # 4. Execute Scene Crowd Engines (Baseline, Global Flow, Partitioning, Local Anomaly, Suppression)
        baseline_ctx = self.crowd_baseline_engine.update_baseline(
            tracks=active_tracks, frame_idx=frame_idx
        )
        flow_info = self.global_flow_engine.compute_flow(
            tracks=active_tracks, camera_motion_vector=global_vector, camera_motion_class=camera_motion_class
        )
        spatial_cells = self.spatial_partitioning_engine.partition_scene(
            tracks=active_tracks, frame_w=w, frame_h=h, global_median_speed=baseline_ctx.median_speed
        )
        anomaly_info = self.local_anomaly_engine.detect_anomalies(
            tracks=active_tracks, baseline_ctx=baseline_ctx
        )
        suppression_info = self.suppression_engine.evaluate_suppression(
            tracks=active_tracks, baseline_ctx=baseline_ctx, global_flow_coherence=flow_info["flow_coherence"]
        )

        # 5. Evidence Accumulation (Requires genuine localized anomaly or strong speed spike, NOT simple crowd)
        has_local_anomaly = len(anomaly_info["anomalous_track_ids"]) > 0
        abnormal_signal = (max_norm_vel > 3.5 and has_local_anomaly) or (interaction_count >= 3 and has_local_anomaly)
        
        # Apply negative evidence suppression to evidence accumulation
        signal_strength = (max_norm_vel / 2.5) * (1.0 - suppression_info["suppression_score"])
        evidence_score = self.evidence_engine.update_evidence(
            event_key="scene_abnormality",
            signal_detected=abnormal_signal,
            signal_strength=signal_strength
        )

        # 6. Build Camera Profile
        res_class = ResolutionClass.HIGH if w >= 1920 else (ResolutionClass.MEDIUM if w >= 1280 else ResolutionClass.LOW)
        fps_class = FpsClass.HIGH if self.fps >= 30 else (FpsClass.MEDIUM if self.fps >= 15 else FpsClass.LOW)

        camera_profile = CameraProfile(
            resolution_class=res_class,
            fps_class=fps_class,
            camera_motion_class=camera_motion_class,
            scene_scale="WIDE",
            apparent_person_scale=DistanceClass.MEDIUM,
            quality_rating="GOOD" if quality.blur_score > 100 else "POOR",
            confidence=0.9
        )

        # 7. Build Scene Profile
        scene_profile = SceneProfile(
            frame_quality=quality,
            camera_profile=camera_profile,
            people_count=len([t for t in active_tracks if t.class_id == 0]),
            tracked_object_count=len(active_tracks),
            crowd_density=crowd_density,
            avg_person_scale=0.05,
            interaction_candidates_count=interaction_count,
            global_motion_class=camera_motion_class,
            scene_stability=0.9 if camera_motion_class == CameraMotionClass.STATIC else 0.4,
            motion_level=round(max_norm_vel, 2)
        )

        # 8. Evaluate Scene State Machine
        scene_state, adaptive_profile = self.scene_state_machine.evaluate(
            scene_profile=scene_profile,
            max_normalized_vel=max_norm_vel,
            evidence_score=evidence_score,
            baseline_ctx=baseline_ctx,
            suppression_info=suppression_info
        )

        return scene_profile, adaptive_profile
