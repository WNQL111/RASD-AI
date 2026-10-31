import logging
import numpy as np

logger = logging.getLogger(__name__)

class CalibrationEngine:
    """
    Translates camera 2D screen coordinates/pixel distances into real-world metrics (meters, km/h).
    Utilizes height ratio calibration or camera focal distance parameters.
    """
    def __init__(self, calibration_data=None):
        self.calibration = calibration_data or {}
        self.height_m = float(self.calibration.get("height_m", 3.0))
        self.angle_deg = float(self.calibration.get("angle_deg", 45.0))
        self.fov_deg = float(self.calibration.get("fov_deg", 80.0))
        self.ppm = float(self.calibration.get("ppm", 50.0))  # Default pixels per meter

    def get_real_distance(self, pixel_distance, bbox_height_px=None):
        """Converts pixel distance to meters."""
        if bbox_height_px and bbox_height_px > 0:
            # Dynamic height estimation: average human height = 1.7 meters
            ppm_at_y = bbox_height_px / 1.7
            return pixel_distance / ppm_at_y
        # Fallback to general pixels per meter
        return pixel_distance / max(1.0, self.ppm)

    def get_real_speed(self, pixel_vel_per_frame, bbox_height_px, fps):
        """Converts pixels/frame velocity into real-world speed in km/h."""
        if fps <= 0:
            fps = 25.0
        # Distance in meters per frame
        distance_m = self.get_real_distance(pixel_vel_per_frame, bbox_height_px)
        # Speed in meters per second
        speed_mps = distance_m * fps
        # Speed in km/h
        speed_kmh = speed_mps * 3.6
        return speed_kmh
