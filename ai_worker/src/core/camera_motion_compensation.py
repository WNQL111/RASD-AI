import cv2
import numpy as np
import logging
from typing import Tuple, List, Optional
from core.scene_types import CameraMotionClass, MotionFeatures

logger = logging.getLogger(__name__)

class CameraMotionAnalyzer:
    """
    Lightweight Camera Motion Compensation Engine for ASIS-V2.
    Estimates global frame shift (dx, dy) using phase correlation / optical flow.
    Categorizes camera motion: STATIC, PAN, TILT, SHAKE, ZOOM.
    Subtracts global motion from object trajectories to get true object-relative motion.
    """
    def __init__(self, max_features: int = 50):
        self.max_features = max_features
        self.prev_gray: Optional[np.ndarray] = None
        self.last_global_vector: List[float] = [0.0, 0.0]
        self.last_motion_class: str = CameraMotionClass.STATIC

    def analyze_frame_motion(self, frame: np.ndarray) -> Tuple[List[float], str]:
        """
        Calculates global motion vector [dx, dy] and camera motion classification.
        Execution budget: < 1.0ms on CPU.
        """
        if frame is None:
            return [0.0, 0.0], CameraMotionClass.STATIC

        try:
            # Convert to grayscale & downsample for ultra-fast motion estimation
            h, w = frame.shape[:2]
            target_w = 320
            scale = target_w / float(w) if w > target_w else 1.0

            if scale < 1.0:
                small_frame = cv2.resize(frame, (target_w, int(h * scale)), interpolation=cv2.INTER_NEAREST)
            else:
                small_frame = frame

            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY) if len(small_frame.shape) == 3 else small_frame

            if self.prev_gray is None or self.prev_gray.shape != gray.shape:
                self.prev_gray = gray
                return [0.0, 0.0], CameraMotionClass.STATIC

            if np.array_equal(self.prev_gray, gray):
                return [0.0, 0.0], CameraMotionClass.STATIC

            # Use Phase Correlation on downsampled image for fast global shift estimation
            shift, response = cv2.phaseCorrelate(np.float32(self.prev_gray), np.float32(gray))
            self.prev_gray = gray

            dx, dy = shift[0] / scale, shift[1] / scale
            magnitude = float(np.hypot(dx, dy))

            # Motion Classification
            motion_class = CameraMotionClass.STATIC
            if magnitude < 1.5:
                motion_class = CameraMotionClass.STATIC
            elif magnitude > 12.0:
                motion_class = CameraMotionClass.SHAKE
            elif abs(dx) > abs(dy) * 1.5:
                motion_class = CameraMotionClass.PAN
            elif abs(dy) > abs(dx) * 1.5:
                motion_class = CameraMotionClass.TILT
            else:
                motion_class = CameraMotionClass.SHAKE

            self.last_global_vector = [round(float(dx), 2), round(float(dy), 2)]
            self.last_motion_class = motion_class

            return self.last_global_vector, self.last_motion_class

        except Exception as e:
            logger.warning(f"CameraMotionAnalyzer: Failed to estimate camera motion ({e}). Defaulting to STATIC.")
            return [0.0, 0.0], CameraMotionClass.STATIC

    def compensate_object_motion(self, raw_center_dx: float, raw_center_dy: float) -> MotionFeatures:
        """
        Subtracts global camera displacement from raw object center displacement.
        Returns camera-compensated MotionFeatures.
        """
        global_dx, global_dy = self.last_global_vector
        rel_dx = raw_center_dx - global_dx
        rel_dy = raw_center_dy - global_dy

        apparent_vel = float(np.hypot(raw_center_dx, raw_center_dy))
        compensated_vel = float(np.hypot(rel_dx, rel_dy))
        direction_rad = float(np.arctan2(rel_dy, rel_dx))

        return MotionFeatures(
            displacement_px=round(compensated_vel, 2),
            apparent_velocity=round(apparent_vel, 2),
            normalized_velocity=round(compensated_vel, 2),
            direction_rad=round(direction_rad, 3),
            global_motion_vector=self.last_global_vector,
            is_camera_motion_compensated=True
        )
