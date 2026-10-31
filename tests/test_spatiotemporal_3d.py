import os
import sys
import unittest
import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_worker', 'src'))

from models_3d.spatiotemporal_3d_net import SpatioTemporal3DNet, Local3DActionModelManager
from core.temporal_3d_verifier import TemporalFrameRingBuffer, CandidateGated3DVerifier

class TestSpatioTemporal3DIntelligence(unittest.TestCase):
    def setUp(self):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

    def test_01_spatiotemporal_net_forward_shapes(self):
        net = SpatioTemporal3DNet(in_channels=3, base_channels=16, feature_dim=128)
        net.eval()
        
        clip = torch.randn(2, 3, 16, 112, 112)
        with torch.no_grad():
            v_prob, c_prob, feats = net(clip)
            
        self.assertEqual(v_prob.shape, (2, 1))
        self.assertEqual(c_prob.shape, (2, 1))
        self.assertEqual(feats.shape, (2, 128))
        
        self.assertTrue((v_prob >= 0.0).all() and (v_prob <= 1.0).all())
        self.assertTrue((c_prob >= 0.0).all() and (c_prob <= 1.0).all())

    def test_02_model_manager_singleton_and_warmup(self):
        manager = Local3DActionModelManager()
        self.assertIsNotNone(manager.model)
        self.assertIn(str(manager.device).split(":")[0], ["cuda", "cpu"])
        
        dummy_clip = torch.randn(1, 3, 16, 112, 112)
        v_p, c_p, emb = manager.infer_action(dummy_clip)
        self.assertIsInstance(v_p, float)
        self.assertIsInstance(c_p, float)
        self.assertEqual(len(emb), 128)

    def test_03_frame_ring_buffer(self):
        buf = TemporalFrameRingBuffer(capacity=30)
        self.assertFalse(buf.is_ready(min_frames=16))
        
        for i in range(20):
            frame = np.full((240, 320, 3), i, dtype=np.uint8)
            buf.push_frame(frame)
            
        self.assertTrue(buf.is_ready(min_frames=16))
        clip_frames = buf.get_window(16)
        self.assertEqual(len(clip_frames), 16)
        self.assertEqual(clip_frames[-1][0, 0, 0], 19)

    def test_04_candidate_gated_verifier_inference(self):
        verifier = CandidateGated3DVerifier(window_size=16)
        
        for i in range(20):
            frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            verifier.push_frame(frame)
            
        # 1. Gated rejection if candidate score is 0
        v_score, c_score, emb = verifier.verify_candidate_roi(
            roi_bbox=[50, 50, 150, 150],
            candidate_confidence=0.0
        )
        self.assertEqual(v_score, 0.0)
        self.assertEqual(c_score, 0.0)
        
        # 2. Real inference when candidate triggers
        v_score_act, c_score_act, emb_act = verifier.verify_candidate_roi(
            roi_bbox=[50, 50, 150, 150],
            candidate_confidence=0.85
        )
        self.assertGreaterEqual(v_score_act, 0.0)
        self.assertGreaterEqual(c_score_act, 0.0)
        self.assertEqual(len(emb_act), 128)

if __name__ == '__main__':
    unittest.main()
