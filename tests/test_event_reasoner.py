import sys
import os
import unittest
import numpy as np

# Ensure ai_worker/src is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))

from core.scene_types import SceneProfile, CameraMotionClass, MotionFeatures
from core.interaction_types import InteractionPair, InteractionState
from core.event_reasoning_types import (
    EventReasoningState, EventLifecycleState, FirewallDecision, EventEvidenceVector
)
from core.false_positive_firewall import FalsePositiveFirewall
from core.multi_signal_evidence_fusion import MultiSignalEvidenceFusionEngine
from core.event_lifecycle_engine import EventLifecycleMachine
from core.temporal_event_reasoner import TemporalEventReasoner
from core.event_reasoning_orchestrator import EventReasoningOrchestrator

class TestEventReasonerAndFirewall(unittest.TestCase):
    def setUp(self):
        self.firewall = FalsePositiveFirewall()
        self.fusion = MultiSignalEvidenceFusionEngine()
        self.lifecycle = EventLifecycleMachine(enter_thresh=0.55, exit_thresh=0.25)
        self.orchestrator = EventReasoningOrchestrator(max_events=20)

    # 1. Behavioral Scenario A & B: Parallel Walking Together Suppression
    def test_01_parallel_walking_together_suppression(self):
        p = InteractionPair(
            track_id_a=1, track_id_b=2,
            direction_score=0.0, relative_velocity=1.5, approach_velocity=0.0
        )
        sp = SceneProfile(people_count=2)

        decision, score, reasons = self.firewall.evaluate_hypothesis(p, sp, persistence_frames=10)
        self.assertEqual(decision, FirewallDecision.SUPPRESS)
        self.assertIn("SUPPRESS_PARALLEL_WALKING_TOGETHER", reasons)

    # 2. Behavioral Scenario C: Separating Tracks Suppression
    def test_02_separating_tracks_suppression(self):
        p = InteractionPair(
            track_id_a=1, track_id_b=2,
            direction_score=0.5, relative_velocity=4.0, approach_velocity=3.5 # Distance opening
        )
        sp = SceneProfile(people_count=2)

        decision, score, reasons = self.firewall.evaluate_hypothesis(p, sp, persistence_frames=10)
        self.assertEqual(decision, FirewallDecision.SUPPRESS)
        self.assertIn("SUPPRESS_SEPARATING_TRACKS", reasons)

    # 3. Behavioral Scenario I: Camera Shake Global Motion Suppression
    def test_03_camera_shake_suppression(self):
        p = InteractionPair(track_id_a=1, track_id_b=2, direction_score=0.5)
        sp = SceneProfile(people_count=2, global_motion_class=CameraMotionClass.SHAKE)

        decision, score, reasons = self.firewall.evaluate_hypothesis(p, sp, persistence_frames=10)
        self.assertIn("SUPPRESS_CAMERA_GLOBAL_MOTION", reasons)

    # 4. Behavioral Scenario D: Short Accidental Contact (Persistence < 5)
    def test_04_short_accidental_contact_hold(self):
        p = InteractionPair(track_id_a=1, track_id_b=2, approach_score=0.5, direction_score=0.5)
        sp = SceneProfile(people_count=2)

        decision, score, reasons = self.firewall.evaluate_hypothesis(p, sp, persistence_frames=2)
        self.assertEqual(decision, FirewallDecision.REQUIRE_MORE_EVIDENCE)
        self.assertIn("HOLD_SHORT_ACCIDENTAL_CONTACT", reasons)

    # 5. Behavioral Scenario F & J: Rapid Head-On Approach Lifecycle (CONFIRMED -> ACTIVE -> ENDED -> COOLDOWN)
    def test_05_event_lifecycle_full_cycle(self):
        p = InteractionPair(
            track_id_a=1, track_id_b=2,
            approach_score=0.9, direction_score=0.9, overlap_score=0.7,
            pose_anomaly_score=0.8, relative_velocity=8.0, approach_velocity=-6.0
        )
        sp = SceneProfile(people_count=2)

        # Frame 1 to 5: Evidence accumulates
        ev_state = None
        for f in range(1, 6):
            ev_state = self.orchestrator.temporal_reasoner.process_pair_event(p, sp, frame_idx=f)

        self.assertIn(ev_state.current_lifecycle_state, [EventLifecycleState.CANDIDATE, EventLifecycleState.CONFIRMED, EventLifecycleState.ACTIVE])

        # Interaction Ends (Separating)
        p_end = InteractionPair(
            track_id_a=1, track_id_b=2,
            approach_score=0.0, direction_score=0.0, overlap_score=0.0,
            approach_velocity=4.0
        )

        for f in range(6, 12):
            ev_state = self.orchestrator.temporal_reasoner.process_pair_event(p_end, sp, frame_idx=f)

        self.assertIn(ev_state.current_lifecycle_state, [EventLifecycleState.ENDING, EventLifecycleState.ENDED, EventLifecycleState.COOLDOWN, EventLifecycleState.REJECTED])

    # 6. Behavioral Scenario G: Crowd Normal Walking (No Event)
    def test_06_crowd_normal_walking_no_event(self):
        p = InteractionPair(track_id_a=1, track_id_b=2, approach_score=0.1, direction_score=0.0)
        sp = SceneProfile(people_count=20, crowd_density=0.6)

        decision, score, reasons = self.firewall.evaluate_hypothesis(p, sp, persistence_frames=10)
        self.assertEqual(decision, FirewallDecision.SUPPRESS)
        self.assertIn("SUPPRESS_CROWD_NORMAL_WALKING", reasons)

    # 7. Occlusion Grace Period Test
    def test_07_occlusion_grace_period(self):
        p = InteractionPair(track_id_a=1, track_id_b=2, approach_score=0.5)
        sp = SceneProfile(people_count=2)

        self.orchestrator.temporal_reasoner.process_pair_event(p, sp, frame_idx=1)
        self.assertIn((1, 2), self.orchestrator.temporal_reasoner.active_events)

        # Missing pair for 10 frames (Grace period active)
        for f in range(2, 12):
            self.orchestrator.temporal_reasoner.handle_occlusion_grace_period(active_pair_keys=set(), frame_idx=f)

        self.assertIn((1, 2), self.orchestrator.temporal_reasoner.active_events)

        # Missing pair for 20 frames (Grace period expired -> Pruned)
        for f in range(12, 25):
            self.orchestrator.temporal_reasoner.handle_occlusion_grace_period(active_pair_keys=set(), frame_idx=f)

        self.assertNotIn((1, 2), self.orchestrator.temporal_reasoner.active_events)

if __name__ == "__main__":
    unittest.main()
