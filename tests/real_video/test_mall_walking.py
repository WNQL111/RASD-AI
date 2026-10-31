import os
import sys
import unittest
import numpy as np
import cv2
import torch

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
AI_WORKER_SRC = os.path.join(BASE_DIR, 'ai_worker', 'src')
if AI_WORKER_SRC not in sys.path:
    sys.path.insert(0, AI_WORKER_SRC)

from detectors.yolo_detector import YoloDetector
from tracker.byte_tracker import ByteTracker
from memory.object_memory import ObjectMemory
from engines.rule_engine import RuleEngine
from core.pipeline import AIPipeline
from core.device_manager import device_manager
from domains.violence.detector import ViolenceDomainDetector
from domains.collision.detector import CollisionDomainDetector

class TestMallWalkingRealVideo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sample_path = os.path.join(BASE_DIR, 'sample_videos', '20260620_174904_mall_waking.mp4')
        root_path = os.path.join(BASE_DIR, '20260620_174904_mall_waking.mp4')
        cls.default_video_path = sample_path if os.path.exists(sample_path) else root_path
        cls.video_path = os.environ.get('ASIS_REAL_VIDEO_PATH', cls.default_video_path)
        cls.detector = YoloDetector(model_dir=os.path.join(BASE_DIR, 'models'), model_name='yolov8n.pt')
        cls.pipeline = AIPipeline(detector=cls.detector)

    def test_01_video_file_integrity_and_properties(self):
        self.assertTrue(os.path.exists(self.video_path), f'Video file not found at: {self.video_path}')
        cap = cv2.VideoCapture(self.video_path)
        self.assertTrue(cap.isOpened(), 'Failed to open real video file with OpenCV')
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()
        
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
        self.assertGreater(fps, 0)
        self.assertGreater(total_frames, 100)
        self.assertGreater(duration, 10.0)

    def test_02_pipeline_execution_and_false_positive_suppression(self):
        cap = cv2.VideoCapture(self.video_path)
        tracker = ByteTracker(self.detector)
        
        confirmed_violence_events = []
        frames_to_test = 300
        
        for frame_idx in range(frames_to_test):
            ret, frame = cap.read()
            if not ret:
                break
            events = self.pipeline.process_frame(frame, frame_idx, 'mall_waking_test', tracker)
            if events:
                for ev in events:
                    if ev.get('type') == 'violence' and ev.get('state') == 'CONFIRMED':
                        confirmed_violence_events.append(ev)
                        
        cap.release()
        self.assertEqual(len(confirmed_violence_events), 0, f'False positive confirmed events triggered: {confirmed_violence_events}')

    def test_03_collision_domain_applicability(self):
        rule_engine = RuleEngine()
        collision_detector = CollisionDomainDetector(rule_engine)
        memory = ObjectMemory()
        events = collision_detector.analyze(memory, frame_idx=1, video_id='mall_waking_test')
        self.assertEqual(len(events), 0)

if __name__ == '__main__':
    unittest.main()
