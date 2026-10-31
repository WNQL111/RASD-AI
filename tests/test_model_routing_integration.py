import sys
import os
import unittest
import numpy as np

# Ensure ai_worker/src is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))

from detectors.yolo_detector import YoloDetector
from tracker.byte_tracker import ByteTracker
from core.pipeline import Pipeline, AdaptiveExecutionController
from core.model_router import model_router

class TestModelRoutingIntegration(unittest.TestCase):
    def setUp(self):
        self.detector = YoloDetector(model_dir="./models", model_name="yolov8n.pt")
        self.pipeline = Pipeline(self.detector)

    def test_pipeline_integration_with_model_router(self):
        # Create dummy static frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        tracker = ByteTracker(self.detector)
        # Process frame 1 (Level 0 Screening)
        res1 = self.pipeline.process_frame(frame, 1, "test_routing_video", tracker)
        self.assertIsInstance(res1, list)

        # Verify router metrics recorded decisions
        metrics = model_router.get_metrics()
        self.assertGreater(metrics["decisions_count"], 0)
        self.assertGreater(metrics["fast_tier_count"], 0)

if __name__ == "__main__":
    unittest.main()
