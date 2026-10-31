import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ai_worker', 'src')))

from memory.object_memory import ObjectMemory
from engines.decision_fusion_engine import DecisionFusionEngine
from engines.risk_scoring_engine import RiskScoringEngine
from plugins.violence import ViolencePlugin
from engines.rule_engine import RuleEngine

class TestAIPipeline(unittest.TestCase):
    """
    Integration Tests for Object Memory, Decision Fusion, Risk Scoring, and Violence Plugin.
    """
    def setUp(self):
        self.rule_engine = RuleEngine()
        self.memory = ObjectMemory()
        self.decision_fusion = DecisionFusionEngine()
        self.risk_engine = RiskScoringEngine()

    def test_object_memory_update(self):
        tracked = [
            {"track_id": 1, "class_id": 0, "confidence": 0.90, "bbox": [100, 100, 150, 250]},
            {"track_id": 2, "class_id": 0, "confidence": 0.88, "bbox": [120, 100, 170, 250]}
        ]
        self.memory.update_frame(tracked, frame_idx=1)
        self.assertIn(1, self.memory.objects)
        self.assertIn(2, self.memory.objects)
        self.assertEqual(self.memory.objects[1].class_id, 0)

    def test_risk_scoring_engine(self):
        risk_info = self.risk_engine.calculate_risk(
            base_confidence=0.85,
            event_type="violence",
            crowd_features={"density": 2, "motion_variance": 10.0},
            matched_zones=[{"type": "Restricted"}]
        )
        self.assertIn("risk_score", risk_info)
        self.assertIn("risk_rating", risk_info)
        self.assertGreaterEqual(risk_info["risk_score"], 0.0)
        self.assertLessEqual(risk_info["risk_score"], 100.0)

    def test_crowd_violence_suppression(self):
        v_plugin = ViolencePlugin(self.rule_engine)
        # Populate memory with two persons walking together
        for i in range(1, 20):
            tracked = [
                {"track_id": 1, "class_id": 0, "confidence": 0.9, "bbox": [100 + i*5, 100, 150 + i*5, 250]},
                {"track_id": 2, "class_id": 0, "confidence": 0.9, "bbox": [120 + i*5, 100, 170 + i*5, 250]}
            ]
            self.memory.update_frame(tracked, frame_idx=i)
        
        crowd_features = {"density": 6, "direction_consistency": 0.95, "motion_variance": 2.0}
        events = v_plugin.analyze(self.memory, frame_idx=20, video_id="test_vid", crowd_features=crowd_features)
        # Should be suppressed (0 violence events for people walking together in an orderly queue/crowd)
        self.assertEqual(len(events), 0)

if __name__ == '__main__':
    unittest.main()
