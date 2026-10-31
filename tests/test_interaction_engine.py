import sys
import os
import unittest
import numpy as np

# Ensure ai_worker/src is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))

from core.scene_types import TrackContext, MotionFeatures, DistanceClass
from core.interaction_types import (
    InteractionPair, InteractionCluster, InteractionState, InteractionEngineResult
)
from core.pair_candidate_generator import PairCandidateGenerator
from core.spatial_relationship_engine import SpatialRelationshipEngine
from core.approach_separation_engine import ApproachSeparationEngine
from core.direction_analysis_engine import DirectionAnalysisEngine
from core.pose_signal_adapter import PoseSignalAdapter
from core.interaction_graph import InteractionGraph
from core.adaptive_interaction_engine import AdaptiveInteractionEngine

class TestAdaptiveInteractionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AdaptiveInteractionEngine(proximity_radius_px=180.0, max_pairs=30)

    # 1. Single Person Test (No pairs generated)
    def test_01_single_person_no_interaction(self):
        t1 = TrackContext(track_id=1, class_id=0, bbox=[10,10,50,50], center=[30,30])
        res = self.engine.process_interactions([t1], frame_idx=1)
        self.assertEqual(len(res.active_pairs), 0)
        self.assertEqual(res.dominant_state, InteractionState.NONE)

    # 2. Two People Far Apart Test
    def test_02_two_people_far_apart(self):
        t1 = TrackContext(track_id=1, class_id=0, bbox=[10,10,50,50], center=[30,30])
        t2 = TrackContext(track_id=2, class_id=0, bbox=[500,500,550,550], center=[525,525])
        res = self.engine.process_interactions([t1, t2], frame_idx=1)
        self.assertEqual(len(res.active_pairs), 0) # Beyond 180px radius

    # 3. Two People Parallel Walking Together (Suppression Rule Test)
    def test_03_parallel_walking_together_suppression(self):
        # Heading angle 0.0 (same direction)
        mf = MotionFeatures(normalized_velocity=2.0, direction_rad=0.0)
        t1 = TrackContext(track_id=1, class_id=0, bbox=[100,100,150,150], center=[125,125], motion_features=mf)
        t2 = TrackContext(track_id=2, class_id=0, bbox=[130,100,180,150], center=[155,125], motion_features=mf)

        res = self.engine.process_interactions([t1, t2], frame_idx=1)
        self.assertEqual(len(res.active_pairs), 1)
        # Suppressed risk score for parallel walking together
        self.assertLessEqual(res.max_pair_risk, 0.15)

    # 4. Rapid Converging Approach Test (Head-on Trajectory)
    def test_04_rapid_headon_converging_approach(self):
        mf_a = MotionFeatures(normalized_velocity=4.0, direction_rad=0.0)      # Moving right ->
        mf_b = MotionFeatures(normalized_velocity=4.0, direction_rad=3.14159) # Moving left <-

        t1 = TrackContext(track_id=1, class_id=0, bbox=[100,100,150,150], center=[125,125], motion_features=mf_a)
        t2 = TrackContext(track_id=2, class_id=0, bbox=[200,100,250,150], center=[225,125], motion_features=mf_b)

        # Frame 1: distance = 100px
        self.engine.process_interactions([t1, t2], frame_idx=1)

        # Frame 2: rapid approach (distance closes to 40px)
        t1.center = [155, 125]
        t2.center = [195, 125]
        res = self.engine.process_interactions([t1, t2], frame_idx=2)

        self.assertEqual(len(res.active_pairs), 1)
        self.assertGreater(res.max_pair_risk, 0.40)
        self.assertTrue(res.pose_trigger_needed)

    # 5. Separating People (Suppression Rule Test)
    def test_05_separating_people_suppression(self):
        t1 = TrackContext(track_id=1, class_id=0, bbox=[100,100,150,150], center=[125,125])
        t2 = TrackContext(track_id=2, class_id=0, bbox=[130,100,180,150], center=[155,125])

        # Frame 1: distance = 30px
        self.engine.process_interactions([t1, t2], frame_idx=1)

        # Frame 2: distance opens to 100px
        t1.center = [80, 125]
        t2.center = [180, 125]
        res = self.engine.process_interactions([t1, t2], frame_idx=2)

        self.assertEqual(len(res.active_pairs), 1)
        self.assertLessEqual(res.max_pair_risk, 0.10) # Suppressed when separating

    # 6. Crowd Mode Clustering Test
    def test_06_crowd_clustering(self):
        t1 = TrackContext(track_id=1, class_id=0, center=[100,100], bbox=[90,90,110,110])
        t2 = TrackContext(track_id=2, class_id=0, center=[130,100], bbox=[120,90,140,110])
        t3 = TrackContext(track_id=3, class_id=0, center=[160,100], bbox=[150,90,170,110])

        res = self.engine.process_interactions([t1, t2, t3], frame_idx=1)
        self.assertGreaterEqual(len(res.clusters), 1)
        self.assertEqual(set(res.clusters[0].track_ids), {1, 2, 3})

    # 7. Operational Scenario 9: Distant person becomes high risk (High Risk Overrides Distance!)
    def test_07_scenario_9_distant_high_risk_override(self):
        mf_a = MotionFeatures(normalized_velocity=6.0, direction_rad=0.0)
        mf_b = MotionFeatures(normalized_velocity=6.0, direction_rad=3.14159)

        # Small distant bounding boxes (VERY_FAR)
        t1 = TrackContext(track_id=1, class_id=0, bbox=[10,10,20,20], center=[15,15], distance_class=DistanceClass.VERY_FAR, motion_features=mf_a)
        t2 = TrackContext(track_id=2, class_id=0, bbox=[100,10,110,20], center=[105,15], distance_class=DistanceClass.VERY_FAR, motion_features=mf_b)

        self.engine.process_interactions([t1, t2], frame_idx=1)
        t1.center = [45, 15]
        t2.center = [75, 15]
        res = self.engine.process_interactions([t1, t2], frame_idx=2)

        # Risk is elevated despite VERY_FAR distance
        self.assertTrue(res.pose_trigger_needed)

    # 8. Pair Bounding Limit Test (Max 30 pairs)
    def test_08_pair_bounding_limit(self):
        tracks = []
        for i in range(20):
            tracks.append(TrackContext(track_id=i, class_id=0, bbox=[100+i*2, 100, 120+i*2, 120], center=[110+i*2, 110]))

        res = self.engine.process_interactions(tracks, frame_idx=1)
        self.assertLessEqual(len(res.active_pairs), 30)

if __name__ == "__main__":
    unittest.main()
