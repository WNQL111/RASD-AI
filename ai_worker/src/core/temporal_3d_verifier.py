import cv2
import time
import math
import logging
import torch
import numpy as np
from collections import deque
from typing import List, Dict, Any, Tuple, Optional
from models_3d.spatiotemporal_3d_net import Local3DActionModelManager

logger = logging.getLogger(__name__)

class TemporalFrameRingBuffer:
    def __init__(self, capacity: int = 30):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)

    def is_ready(self, min_frames: int = 16) -> bool:
        return len(self.buffer) >= min_frames

    def get_window(self, window_size: int = 16) -> List[np.ndarray]:
        return self.get_recent_frames(window_size)

    def get_temporal_window(self, window_size: int = 16) -> List[np.ndarray]:
        return self.get_recent_frames(window_size)

    def push_frame(self, frame: np.ndarray):
        self.append(len(self.buffer), frame)

    def add_frame(self, frame: np.ndarray):
        self.append(len(self.buffer), frame)

    def append(self, frame_idx: int, frame: np.ndarray, timestamp_sec: float = 0.0):
        if frame is not None:
            self.buffer.append({
                "frame_idx": frame_idx,
                "frame": frame.copy(),
                "timestamp_sec": timestamp_sec
            })

    def get_recent_frames(self, num_frames: int = 16) -> List[np.ndarray]:
        if len(self.buffer) == 0:
            return []
        items = list(self.buffer)[-num_frames:]
        frames = [item["frame"] for item in items]
        while len(frames) < num_frames:
            frames.insert(0, frames[0])
        return frames

class CandidateGated3DVerifier:
    def __init__(self, window_size: int = 16, temporal_window: int = 16, candidate_threshold: float = 0.45, model_dir: str = "/app/models", **kwargs):
        self.temporal_length = window_size or temporal_window
        self.model_manager = Local3DActionModelManager(model_dir=model_dir)
        self.ring_buffers: Dict[str, TemporalFrameRingBuffer] = {}
        self.target_size = (112, 112)
        self.main_buffer = TemporalFrameRingBuffer(capacity=30)

    def push_frame(self, frame: np.ndarray):
        self.main_buffer.append(len(self.main_buffer.buffer), frame)

    def add_frame(self, frame: np.ndarray, frame_idx: int = 0, stream_id: str = "default"):
        self.push_frame(frame)
        if stream_id not in self.ring_buffers:
            self.ring_buffers[stream_id] = TemporalFrameRingBuffer(capacity=30)
        self.ring_buffers[stream_id].append(frame_idx, frame)

    def get_or_create_buffer(self, stream_id: str) -> TemporalFrameRingBuffer:
        if stream_id not in self.ring_buffers:
            self.ring_buffers[stream_id] = TemporalFrameRingBuffer(capacity=30)
        return self.ring_buffers[stream_id]

    def record_frame(self, stream_id: str, frame_idx: int, frame: np.ndarray, timestamp_sec: float = 0.0):
        buf = self.get_or_create_buffer(stream_id)
        buf.append(frame_idx, frame, timestamp_sec)

    def extract_roi_volume(self, frames: List[np.ndarray], union_bbox: List[float]) -> torch.Tensor:
        x1, y1, x2, y2 = map(int, union_bbox)
        t_frames = []

        for frame in frames:
            fh, fw = frame.shape[:2]
            margin_x = int((x2 - x1) * 0.15)
            margin_y = int((y2 - y1) * 0.15)
            
            crop_x1 = max(0, x1 - margin_x)
            crop_y1 = max(0, y1 - margin_y)
            crop_x2 = min(fw, x2 + margin_x)
            crop_y2 = min(fh, y2 + margin_y)

            if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                cropped = frame[crop_y1:crop_y2, crop_x1:crop_x2]
            else:
                cropped = frame

            resized = cv2.resize(cropped, self.target_size)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            normalized = rgb.astype(np.float32) / 255.0
            t_frames.append(normalized)

        while len(t_frames) < self.temporal_length:
            t_frames.append(t_frames[-1] if t_frames else np.zeros((112, 112, 3), dtype=np.float32))

        clip_np = np.stack(t_frames[:self.temporal_length], axis=0) # [T, H, W, C]
        clip_np = np.transpose(clip_np, (3, 0, 1, 2))              # [C, T, H, W]
        clip_tensor = torch.from_numpy(clip_np).unsqueeze(0).float() # [1, C, T, H, W]
        return clip_tensor

    def verify_candidate_roi(self, roi_bbox: List[float], candidate_confidence: float = 0.85, domain: str = "violence") -> Tuple[float, float, List[float]]:
        if candidate_confidence < 0.40 or len(self.main_buffer.buffer) < 16:
            return 0.0, 0.0, [0.0] * 128
        frames = self.main_buffer.get_recent_frames(self.temporal_length)
        vol = self.extract_roi_volume(frames, roi_bbox)
        return self.model_manager.infer_action(vol)

    def verify_candidate_action(
        self,
        stream_id: str,
        domain: str,
        bboxes: List[List[float]],
        current_frame_idx: int
    ) -> Tuple[float, Dict[str, Any]]:
        buf = self.ring_buffers.get(stream_id)
        if not buf or len(buf.buffer) < 8:
            if len(self.main_buffer.buffer) >= 8:
                buf = self.main_buffer
            else:
                return 0.0, {"status": "INSUFFICIENT_BUFFER_FRAMES"}

        frames = buf.get_recent_frames(self.temporal_length)
        if not frames:
            return 0.0, {"status": "EMPTY_FRAMES"}

        if len(bboxes) >= 2:
            u_x1 = min(b[0] for b in bboxes)
            u_y1 = min(b[1] for b in bboxes)
            u_x2 = max(b[2] for b in bboxes)
            u_y2 = max(b[3] for b in bboxes)
            union_bbox = [u_x1, u_y1, u_x2, u_y2]
        elif len(bboxes) == 1:
            union_bbox = bboxes[0]
        else:
            union_bbox = [0, 0, frames[0].shape[1], frames[0].shape[0]]

        start_t = time.time()
        clip_tensor = self.extract_roi_volume(frames, union_bbox)
        score_3d = self.model_manager.verify_clip(clip_tensor, domain=domain)
        latency_ms = round((time.time() - start_t) * 1000, 2)

        meta = {
            "domain": domain,
            "score_3d": score_3d,
            "latency_ms": latency_ms,
            "frames_evaluated": len(frames),
            "device": str(self.model_manager.device)
        }
        return score_3d, meta
