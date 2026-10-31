import sys
import os
import unittest

# Ensure ai_worker/src is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))

from core.routing_types import (
    ModelSpec, RoutingContext, RoutingDecision, ModelTask, ModelTier, ModelStatus
)
from core.model_registry import ModelRegistry, model_registry
from core.routing_policy import RoutingPolicy
from core.model_router import ModelRouter, model_router

class TestModelRegistryAndRouter(unittest.TestCase):
    def setUp(self):
        self.registry = ModelRegistry(model_dir="./models")
        self.registry._register_default_models()
        self.router = ModelRouter()
        self.router.enabled = True
        self.router.policy = RoutingPolicy()
        self.router.last_decision = None
        self.router.hysteresis_counter = 0

    def test_registry_registration_and_retrieval(self):
        spec = self.registry.get_spec("yolov8n.pt")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.tier, ModelTier.FAST)
        self.assertEqual(spec.task, ModelTask.OBJECT_DETECTION)

    def test_case_1_normal_level0_screening_routes_to_fast(self):
        ctx = RoutingContext(current_level="LEVEL_0_SCREENING", risk_state="LOW")
        decision = self.router.select_model(ctx)
        self.assertEqual(decision.selected_model, "yolov8n.pt")
        self.assertEqual(decision.tier, ModelTier.FAST)
        self.assertFalse(decision.run_pose)

    def test_case_2_level1_detection_routes_to_fast(self):
        ctx = RoutingContext(current_level="LEVEL_1_DETECTION", risk_state="LOW")
        decision = self.router.select_model(ctx)
        self.assertEqual(decision.selected_model, "yolov8n.pt")
        self.assertEqual(decision.tier, ModelTier.FAST)

    def test_case_3_level2_interaction_routes_to_fast(self):
        ctx = RoutingContext(current_level="LEVEL_2_INTERACTION", track_count=2)
        decision = self.router.select_model(ctx)
        self.assertEqual(decision.selected_model, "yolov8n.pt")
        self.assertEqual(decision.tier, ModelTier.FAST)

    def test_case_4_level3_forensic_routes_to_balanced(self):
        ctx = RoutingContext(current_level="LEVEL_3_FORENSIC", risk_state="HIGH", pose_needed=True)
        decision = self.router.select_model(ctx)
        self.assertEqual(decision.selected_model, "yolov8m.pt")
        self.assertEqual(decision.tier, ModelTier.BALANCED)
        self.assertTrue(decision.run_pose)

    def test_case_5_unavailable_model_triggers_fallback(self):
        # Mark yolov8m as UNAVAILABLE temporarily
        spec = self.registry.get_spec("yolov8m.pt")
        original_status = spec.status
        spec.status = ModelStatus.UNAVAILABLE

        try:
            ctx = RoutingContext(current_level="LEVEL_3_FORENSIC", risk_state="HIGH")
            decision = self.router.select_model(ctx)
            self.assertEqual(decision.selected_model, "yolov8n.pt")
            self.assertEqual(decision.tier, ModelTier.FAST)
            self.assertIn("fallback", decision.reason)
        finally:
            spec.status = original_status

    def test_case_6_gpu_vram_limit_triggers_resource_constrained_downgrade(self):
        # Simulate 95% VRAM utilization (> 85% limit)
        ctx = RoutingContext(
            current_level="LEVEL_3_FORENSIC",
            gpu_memory_used_mb=3900.0,
            gpu_memory_total_mb=4096.0
        )
        decision = self.router.select_model(ctx)
        self.assertEqual(decision.selected_model, "yolov8n.pt")
        self.assertEqual(decision.tier, ModelTier.FAST)
        self.assertIn("resource_constrained", decision.reason)

    def test_case_7_router_exception_triggers_fail_safe_fallback(self):
        # Test exception safety
        policy = RoutingPolicy()
        policy.evaluate = lambda ctx: 1 / 0 # Force ZeroDivisionError

        test_router = ModelRouter()
        test_router.policy = policy
        ctx = RoutingContext(current_level="LEVEL_3_FORENSIC")
        decision = test_router.select_model(ctx)

        self.assertEqual(decision.selected_model, "yolov8n.pt")
        self.assertIn("fail_safe_fallback", decision.reason)

    def test_case_8_pose_not_needed(self):
        ctx = RoutingContext(current_level="LEVEL_1_DETECTION", pose_needed=False)
        decision = self.router.select_model(ctx)
        self.assertFalse(decision.run_pose)

    def test_case_9_pose_needed(self):
        ctx = RoutingContext(current_level="LEVEL_3_FORENSIC", pose_needed=True)
        decision = self.router.select_model(ctx)
        if not decision.run_pose:
            print("DEBUG test_case_9:", decision.to_dict())
        self.assertTrue(decision.run_pose)

    def test_case_10_hysteresis_demotion_cooldown(self):
        # Step A: High Tier (LEVEL_3)
        ctx_high = RoutingContext(current_level="LEVEL_3_FORENSIC", risk_state="HIGH")
        d1 = self.router.select_model(ctx_high)
        self.assertEqual(d1.tier, ModelTier.BALANCED)

        # Step B: Immediate Drop to LEVEL_0 (Hysteresis should retain BALANCED)
        ctx_low = RoutingContext(current_level="LEVEL_0_SCREENING", risk_state="LOW")
        d2 = self.router.select_model(ctx_low)
        self.assertEqual(d2.tier, ModelTier.BALANCED)
        self.assertIn("hysteresis_retained", d2.reason)

if __name__ == "__main__":
    unittest.main()
