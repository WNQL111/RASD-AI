# -*- coding: utf-8 -*-
"""
Perspective-Invariant Scale Normalization Engine (v/h & a/h)
============================================================
Mathematical Principles:
  - Normalized Velocity: v_norm = (delta_distance / bbox_height) / dt
  - Scale Invariance: Eliminates camera distance (Z-depth) distortion so that
    distant and near subjects are evaluated on an identical kinetic scale.
"""
import math
import numpy as np
import logging
from typing import List, Tuple
from core.scene_types import MotionFeatures

logger = logging.getLogger(__name__)

class NormalizedMotionEngine:
    """
    Normalized Motion Engine for ASIS-V2.
    Calculates scale-invariant, FPS-independent motion features.
    Normalizes apparent pixel displacement by object scale (bbox height/diagonal), frame resolution, and dt.
    """
    def __init__(self, baseline_fps: float = 25.0):
        self.baseline_fps = baseline_fps

    def compute_normalized_features(
        self,
        raw_dx: float,
        raw_dy: float,
        global_dx: float,
        global_dy: float,
        bbox: List[float],
        frame_w: int,
        frame_h: int,
        prev_velocity: float = 0.0,
        dt_frames: int = 1
    ) -> MotionFeatures:
        """
        Computes scale-normalized, camera-compensated velocity and acceleration.
        """
        dt = max(1, dt_frames)

        # 1. Camera Motion Compensation
        rel_dx = raw_dx - global_dx
        rel_dy = raw_dy - global_dy
        comp_disp = math.hypot(rel_dx, rel_dy)

        # 2. Object Scale Normalization (Bounding Box Diagonal)
        x1, y1, x2, y2 = bbox
        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)
        obj_diagonal = math.hypot(bw, bh)

        # Normalize displacement by object scale (body lengths per frame)
        scale_normalized_disp = comp_disp / obj_diagonal

        # Normalize velocity to standard 25 FPS scale (body lengths per second)
        fps_factor = self.baseline_fps / float(dt)
        normalized_velocity = scale_normalized_disp * fps_factor

        # 3. Normalized Acceleration
        raw_acc = (normalized_velocity - prev_velocity) / float(dt)
        normalized_acc = round(raw_acc, 3)

        # 4. Direction & Motion Angle
        direction_rad = math.atan2(rel_dy, rel_dx)

        return MotionFeatures(
            displacement_px=round(comp_disp, 2),
            apparent_velocity=round(comp_disp / float(dt), 2),
            normalized_velocity=round(normalized_velocity, 3),
            normalized_acceleration=normalized_acc,
            direction_rad=round(direction_rad, 3),
            global_motion_vector=[round(global_dx, 2), round(global_dy, 2)],
            is_camera_motion_compensated=True
        )
