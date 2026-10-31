import math
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from core.interaction_types import InteractionPair, PoseJointFeatures

logger = logging.getLogger(__name__)

class PoseSignalAdapter:
    """
    Selective Pose Signal Adapter for ASIS-V2.
    Extracts joint features (wrist velocity, arm acceleration, torso asymmetry) ONLY when triggered by interaction candidates.
    Does NOT run Pose globally across static frames.
    """
    def extract_pose_features(self, keypoints: List[Tuple[float, float, float]]) -> PoseJointFeatures:
        """
        Extracts joint features from 17-keypoint YOLO-Pose format.
        Keypoint indices: 5,6 (shoulders), 7,8 (elbows), 9,10 (wrists), 11,12 (hips).
        """
        if not keypoints or len(keypoints) < 17:
            return PoseJointFeatures()

        try:
            # Wrists (9=left wrist, 10=right wrist)
            lw, rw = keypoints[9], keypoints[10]
            # Shoulders (5=left shoulder, 6=right shoulder)
            ls, rs = keypoints[5], keypoints[6]

            # Upper body motion & wrist displacement
            wrist_dist = math.hypot(lw[0] - rw[0], lw[1] - rw[1])
            shoulder_dist = max(1.0, math.hypot(ls[0] - rs[0], ls[1] - rs[1]))

            # Torso asymmetry (vertical shoulder tilt angle)
            shoulder_tilt = abs(ls[1] - rs[1]) / shoulder_dist

            # Normalized wrist elevation relative to shoulders
            wrist_raised = float(lw[1] < ls[1] or rw[1] < rs[1])

            anomaly_score = round(min(1.0, (shoulder_tilt * 1.5) + (wrist_raised * 0.4)), 3)

            return PoseJointFeatures(
                wrist_velocity=round(wrist_dist / shoulder_dist, 2),
                arm_acceleration=round(shoulder_tilt, 2),
                torso_asymmetry=round(shoulder_tilt, 2),
                upper_body_motion=anomaly_score,
                pose_confidence=0.85
            )
        except Exception as e:
            logger.warning(f"PoseSignalAdapter: Joint feature extraction error ({e})")
            return PoseJointFeatures()

    def evaluate_pair_pose_anomaly(
        self,
        pair: InteractionPair,
        pose_data_a: Optional[List[Any]],
        pose_data_b: Optional[List[Any]]
    ) -> float:
        """
        Calculates joint pose anomaly score for a pair.
        """
        feat_a = self.extract_pose_features(pose_data_a) if pose_data_a else PoseJointFeatures()
        feat_b = self.extract_pose_features(pose_data_b) if pose_data_b else PoseJointFeatures()

        pair.pose_anomaly_score = round(max(feat_a.upper_body_motion, feat_b.upper_body_motion), 3)
        return pair.pose_anomaly_score
