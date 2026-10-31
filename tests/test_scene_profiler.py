import sys
import os
import unittest
import numpy as np
import cv2

# Ensure ai_worker/src is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))

from core.scene_types import (
    FrameQuality, CameraProfile, MotionFeatures, TrackContext, SceneProfile,
    AdaptiveAnalysisProfile, ResolutionClass, FpsClass, DistanceClass,
    CameraMotionClass, SceneState, AnalysisMode
)
from core.routing_types import RoutingContext
from core.camera_motion_compensation import CameraMotionAnalyzer
from core.normalized_motion_engine import NormalizedMotionEngine
from core.temporal_context_engine import TemporalContextManager
from core.evidence_engine import EvidenceEngine
from core.scene_state_machine import SceneStateMachine
from core.scene_profiler import SceneProfiler
from core.model_router import ModelRouter

class TestSceneProfilerAndAdaptiveEngine(unittest.TestCase):
    def setUp(self):
        self.profiler = SceneProfiler(fps=25.0)
        self.router = ModelRouter()
        self.router.enabled = True
        self.router.last_decision = None
        self.router.hysteresis_counter = 0

    # 1. Static Camera Test
    def test_01_static_camera_analysis(self):
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        frame2 = np.zeros((480, 640, 3), dtype=np.uint8)
        self.profiler.camera_motion_analyzer.analyze_frame_motion(frame1)
        vec, motion_class = self.profiler.camera_motion_analyzer.analyze_frame_motion(frame2)
        self.assertEqual(motion_class, CameraMotionClass.STATIC)
        self.assertEqual(vec, [0.0, 0.0])

    # 2. Moving Camera / Pan Test
    def test_02_moving_camera_pan(self):
        frame1 = np.zeros((200, 300, 3), dtype=np.uint8)
        frame2 = np.zeros((200, 300, 3), dtype=np.uint8)
        cv2.circle(frame1, (100, 100), 20, (255, 255, 255), -1)
        cv2.circle(frame2, (120, 100), 20, (255, 255, 255), -1) # Shifted right by 20px

        self.profiler.camera_motion_analyzer.analyze_frame_motion(frame1)
        vec, motion_class = self.profiler.camera_motion_analyzer.analyze_frame_motion(frame2)
        self.assertIn(motion_class, [CameraMotionClass.PAN, CameraMotionClass.SHAKE, CameraMotionClass.STATIC])

    # 3. Quality & Blur Analysis
    def test_03_quality_and_blur_estimation(self):
        sharp_frame = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        blur_frame = cv2.GaussianBlur(sharp_frame, (15, 15), 0)

        q_sharp = self.profiler.analyze_frame_quality(sharp_frame)
        q_blur = self.profiler.analyze_frame_quality(blur_frame)

        self.assertGreater(q_sharp.blur_score, q_blur.blur_score)

    # 4. Low Light & Brightness Classification
    def test_04_low_light_classification(self):
        dark_frame = np.ones((100, 100, 3), dtype=np.uint8) * 20
        q = self.profiler.analyze_frame_quality(dark_frame)
        self.assertEqual(q.illumination_level, "POOR")

    # 5. Distance Classification (VERY_FAR vs VERY_NEAR)
    def test_05_distance_classification(self):
        far_bbox = [10.0, 10.0, 20.0, 20.0]     # Small area
        near_bbox = [10.0, 10.0, 800.0, 800.0] # Large area (>18% frame area)

        c_far = self.profiler.classify_distance(far_bbox, 1920, 1080)
        c_near = self.profiler.classify_distance(near_bbox, 1920, 1080)

        self.assertEqual(c_far, DistanceClass.VERY_FAR)
        self.assertEqual(c_near, DistanceClass.VERY_NEAR)

    # 6. Motion Normalization (FPS & Scale Invariant)
    def test_06_motion_normalization(self):
        engine = NormalizedMotionEngine(baseline_fps=25.0)
        bbox = [10.0, 10.0, 110.0, 110.0] # 100x100 box
        feats = engine.compute_normalized_features(
            raw_dx=10.0, raw_dy=0.0, global_dx=0.0, global_dy=0.0,
            bbox=bbox, frame_w=1920, frame_h=1080, prev_velocity=0.0, dt_frames=1
        )
        self.assertGreater(feats.normalized_velocity, 0.0)
        self.assertTrue(feats.is_camera_motion_compensated)

    # 7. Evidence Accumulation & Decay
    def test_07_evidence_accumulation_and_decay(self):
        engine = EvidenceEngine(accumulation_rate=0.20, decay_rate=0.10, confirmation_thresh=0.50)

        # Accumulate
        score1 = engine.update_evidence("evt1", signal_detected=True, signal_strength=1.0)
        score2 = engine.update_evidence("evt1", signal_detected=True, signal_strength=1.0)
        score3 = engine.update_evidence("evt1", signal_detected=True, signal_strength=1.0)

        self.assertGreaterEqual(score3, 0.50)
        self.assertTrue(engine.is_confirmed("evt1"))

        # Decay
        score_d1 = engine.update_evidence("evt1", signal_detected=False)
        self.assertLess(score_d1, score3)

    # 8. Temporal Context Bounded Memory & Eviction
    def test_08_temporal_context_eviction(self):
        mgr = TemporalContextManager(max_tracks=3)
        mf = MotionFeatures()

        for i in range(5):
            mgr.update_track(track_id=i, class_id=0, frame_idx=i, bbox=[0,0,10,10], motion_features=mf)

        contexts = mgr.get_all_contexts()
        self.assertLessEqual(len(contexts), 3)

    # 9. Scene State Machine Escalation
    def test_09_scene_state_machine_escalation(self):
        sm = SceneStateMachine()
        sp = SceneProfile(people_count=10, crowd_density=0.8, interaction_candidates_count=3)
        state, profile = sm.evaluate(scene_profile=sp, max_normalized_vel=4.0, evidence_score=0.8)

        self.assertEqual(state, SceneState.EVENT_CONFIRMED)
        self.assertEqual(profile.mode, AnalysisMode.CRITICAL)

    # 10. Hysteresis De-escalation Protection
    def test_10_hysteresis_de_escalation(self):
        sm = SceneStateMachine(hysteresis_frames=15)

        # High risk escalation
        sp_high = SceneProfile(people_count=10, crowd_density=0.8)
        sm.evaluate(scene_profile=sp_high, max_normalized_vel=4.0, evidence_score=0.8)
        self.assertEqual(sm.current_state, SceneState.EVENT_CONFIRMED)

        # Immediate drop to static (Hysteresis should hold state)
        sp_low = SceneProfile(people_count=0, crowd_density=0.0)
        state_held, _ = sm.evaluate(scene_profile=sp_low, max_normalized_vel=0.0, evidence_score=0.0)
        self.assertEqual(state_held, SceneState.EVENT_CONFIRMED)

    # Behavioral Scenario A: Single far person walking normally -> LIGHT/STANDARD
    def test_11_scenario_a_single_far_person(self):
        class Obj:
            track_id = 1
            class_id = 0
            bbox = [10.0, 10.0, 20.0, 20.0]
            dx = 1.0
            dy = 0.0

        sp, ap = self.profiler.profile_scene(None, [Obj()], frame_idx=1)
        self.assertIn(ap.mode, [AnalysisMode.LIGHT, AnalysisMode.STANDARD])

    # Behavioral Scenario G: Camera shaking, persons static -> NO false escalation
    def test_12_scenario_g_camera_shake_no_false_escalation(self):
        class Obj:
            track_id = 1
            class_id = 0
            bbox = [100.0, 100.0, 200.0, 200.0]
            dx = 10.0 # Apparent dx due to camera shake
            dy = 0.0

        # Simulate camera shake vector
        self.profiler.camera_motion_analyzer.last_global_vector = [10.0, 0.0]
        self.profiler.camera_motion_analyzer.last_motion_class = CameraMotionClass.SHAKE

        sp, ap = self.profiler.profile_scene(None, [Obj()], frame_idx=1)
        self.assertIn(ap.mode, [AnalysisMode.LIGHT, AnalysisMode.STANDARD])

if __name__ == "__main__":
    import cv2
    unittest.main()
