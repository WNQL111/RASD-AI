import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MotionGate:
    def __init__(
        self,
        motion_threshold: float = 0.003,
        pixel_change_threshold: float = 0.005,
        scene_change_threshold: float = 0.40
    ):
        self.motion_threshold = motion_threshold
        self.pixel_change_threshold = pixel_change_threshold
        self.scene_change_threshold = scene_change_threshold
        
        self.last_gray = None
        self.last_frame_shape = None

    def reset(self):
        self.last_gray = None
        self.last_frame_shape = None

    def evaluate_frame(self, frame: np.ndarray) -> dict:
        if frame is None or frame.size == 0:
            return {
                "motion_score": 0.0,
                "changed_pixel_ratio": 0.0,
                "activity_detected": False,
                "scene_change": False,
                "confidence": 0.0
            }

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        gray_blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        if self.last_gray is None or self.last_gray.shape != gray_blurred.shape:
            self.last_gray = gray_blurred
            self.last_frame_shape = gray.shape
            return {
                "motion_score": 1.0,
                "changed_pixel_ratio": 1.0,
                "activity_detected": True,
                "scene_change": True,
                "confidence": 1.0
            }

        frame_diff = cv2.absdiff(self.last_gray, gray_blurred)
        _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        
        non_zero_count = cv2.countNonZero(thresh)
        total_pixels = gray_blurred.shape[0] * gray_blurred.shape[1]
        changed_ratio = non_zero_count / float(total_pixels)
        
        self.last_gray = gray_blurred

        is_scene_cut = changed_ratio >= self.scene_change_threshold
        is_activity = changed_ratio >= self.pixel_change_threshold

        return {
            "motion_score": round(changed_ratio, 4),
            "changed_pixel_ratio": round(changed_ratio, 4),
            "activity_detected": is_activity,
            "scene_change": is_scene_cut,
            "confidence": 1.0
        }

    def check_motion(self, frame: np.ndarray):
        res = self.evaluate_frame(frame)
        return res.get("activity_detected", False), res.get("changed_pixel_ratio", 0.0)
