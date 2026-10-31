import unittest
import numpy as np
import time
import os
import sys
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_worker', 'src'))

from core.motion_gate import MotionGate
from engines.rule_engine import RuleEngine
from memory.object_memory import ObjectMemory, ObjectState
from core.pipeline import AdaptiveExecutionController, Pipeline

class TestPhase2AdaptiveAnalysis(unittest.TestCase):
    """
    Automated integration tests for Phase 2 Adaptive Intelligent Video Analysis.
    Verifies MotionGate screening, 5-Tier level escalation/downgrade, hysteresis cooldown,
    ring buffer pre-event history, velocity dt normalization, and skip ratio telemetry.
    """
    
    def setUp(self):
        self.rule_engine = RuleEngine()
        self.motion_gate = MotionGate()
        self.controller = AdaptiveExecutionController(self.rule_engine)
        self.memory = ObjectMemory()

    def test_motion_gate_static_vs_motion_frame(self):
        # Frame 1: Blank black image
        f1 = np.zeros((480, 640, 3), dtype=np.uint8)
        res1 = self.motion_gate.evaluate_frame(f1)
        self.assertTrue(res1["activity_detected"]) # Initial baseline frame

        # Frame 2: Identical black image (Static background)
        f2 = np.zeros((480, 640, 3), dtype=np.uint8)
        res2 = self.motion_gate.evaluate_frame(f2)
        self.assertFalse(res2["activity_detected"]) # Zero motion detected
        self.assertEqual(res2["changed_pixel_ratio"], 0.0)

        # Frame 3: Image with white rectangle added (Active motion)
        f3 = np.zeros((480, 640, 3), dtype=np.uint8)
        f3[100:200, 100:200] = 255
        res3 = self.motion_gate.evaluate_frame(f3)
        self.assertTrue(res3["activity_detected"]) # Motion detected!
        self.assertGreater(res3["changed_pixel_ratio"], 0.01)

    def test_adaptive_5_tier_escalation_and_hysteresis(self):
        f_static = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 1. Level 0 Screening on static frame
        self.motion_gate.reset()
        self.controller.reset()
        
        # Reset initial frame
        lvl0 = self.controller.evaluate_frame_level(f_static, self.memory)
        # Next identical static frame -> LEVEL_0
        lvl0_static = self.controller.evaluate_frame_level(f_static, self.memory)
        self.assertEqual(lvl0_static, AdaptiveExecutionController.LEVEL_0)

        # 2. Add active motion -> Escalate to LEVEL_1
        f_motion = f_static.copy()
        f_motion[100:300, 100:300] = 255
        lvl1 = self.controller.evaluate_frame_level(f_motion, self.memory)
        self.assertEqual(lvl1, AdaptiveExecutionController.LEVEL_1)

        # 3. Add person object -> Escalate to LEVEL_2
        self.memory.update_frame([{'track_id': 1, 'class_id': 0, 'bbox': [50, 50, 100, 150]}], 10)
        lvl2 = self.controller.evaluate_frame_level(f_motion, self.memory)
        self.assertEqual(lvl2, AdaptiveExecutionController.LEVEL_2)

        # 4. High proximity / high velocity -> Escalate to LEVEL_3
        state = self.memory.objects[1]
        state.velocity = 10.0 # High velocity trigger
        lvl3 = self.controller.evaluate_frame_level(f_motion, self.memory)
        self.assertEqual(lvl3, AdaptiveExecutionController.LEVEL_3)

        # 5. Remove velocity/motion -> Hysteresis cooldown holds LEVEL_3
        state.velocity = 0.0
        self.memory.objects.clear()
        lvl_hysteresis = self.controller.evaluate_frame_level(f_static, self.memory)
        self.assertEqual(lvl_hysteresis, AdaptiveExecutionController.LEVEL_3) # Held by hysteresis!

    def test_object_memory_velocity_dt_normalization(self):
        obj_state = ObjectState(track_id=1, class_id=0, bbox=[100, 100, 150, 200], frame_idx=0)
        
        # Move 50 pixels in 1 frame step (df = 1) -> velocity = 50.0
        obj_state.update(bbox=[150, 100, 200, 200], frame_idx=1)
        self.assertAlmostEqual(obj_state.velocity, 50.0, places=1)

        # Move 50 pixels in 5 frame steps under sparse sampling (df = 5) -> normalized velocity = 10.0
        obj_state.update(bbox=[200, 100, 250, 200], frame_idx=6)
        self.assertAlmostEqual(obj_state.velocity, 10.0, places=1)

    def test_ring_buffer_pre_event_history(self):
        ring_buffer = deque(maxlen=30)
        for i in range(50):
            dummy_frame = np.zeros((100, 100), dtype=np.uint8)
            ring_buffer.append((i, dummy_frame))

        self.assertEqual(len(ring_buffer), 30)
        self.assertEqual(ring_buffer[0][0], 20) # Frame 20 to 49 retained
        self.assertEqual(ring_buffer[-1][0], 49)

    def test_telemetry_skip_ratio_calculation(self):
        self.controller.metrics["total_decoded_frames"] = 100
        self.controller.metrics["screened_frames"] = 100
        self.controller.metrics["yolo_frames"] = 20
        self.controller.metrics["skipped_frames"] = 80

        total_dec = self.controller.metrics["total_decoded_frames"]
        skip_ratio = round(self.controller.metrics["skipped_frames"] / total_dec, 3)
        yolo_red = round(1.0 - (self.controller.metrics["yolo_frames"] / total_dec), 3)

        self.assertEqual(skip_ratio, 0.80) # 80% skipped
        self.assertEqual(yolo_red, 0.80)   # 80% YOLO reduction

if __name__ == "__main__":
    unittest.main()
