import os
import cv2
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Bounded ThreadPoolExecutor (max 2 workers) to isolate background video encoding
# and prevent thread leaks, CPU spikes, or disk contention during alert bursts.
_clip_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="clip_encoder")

class VideoClipEngine:
    """
    Slices event video clips (5s pre-event, 10s post-event)
    for both uploaded files and live streams natively using OpenCV and FFmpeg.
    Decoupled from the AI Hot Path via asynchronous background execution.
    """
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            candidates = [
                "/app/data/videos/clips",
                os.path.join(os.getcwd(), "data", "videos", "clips"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "videos", "clips")
            ]
            resolved = candidates[0]
            for c in candidates:
                if os.path.exists(os.path.dirname(c)) or os.path.exists(c):
                    resolved = c
                    break
            self.output_dir = resolved
        else:
            self.output_dir = output_dir
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create clips directory: {e}")

    def create_clip_from_video(self, source_path: str, event_id: str, event_frame: int, fps: float, pre_sec: float = 5.0, post_sec: float = 10.0) -> str:
        """
        Dispatches video clip slicing and H.264 web encoding to a background worker thread.
        Returns the expected relative clip URL instantly without blocking the AI inference loop.
        """
        filename = f"{event_id}_clip.mp4"
        out_path = os.path.join(self.output_dir, filename)

        # Dispatch background encoding task asynchronously
        _clip_executor.submit(
            self._process_clip_background,
            source_path, out_path, event_id, event_frame, fps, pre_sec, post_sec
        )

        # Returns clip path relative to static serving mount (/videos) instantly
        return f"/videos/clips/{filename}"

    def _process_clip_background(self, source_path: str, out_path: str, event_id: str, event_frame: int, fps: float, pre_sec: float, post_sec: float):
        """Worker method executing frame slicing and FFmpeg H.264 encoding off the Hot Path."""
        try:
            cap = cv2.VideoCapture(source_path)
            if not cap.isOpened():
                logger.error(f"Failed to open source video for clip background task: {source_path}")
                return

            pre_frames = int(pre_sec * fps)
            post_frames = int(post_sec * fps)
            
            start_frame = max(0, event_frame - pre_frames)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            end_frame = min(total_frames, event_frame + post_frames) if total_frames > 0 else event_frame + post_frames

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if width <= 0 or height <= 0:
                width, height = 640, 480

            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(out_path, fourcc, fps if fps > 0 else 25.0, (width, height))

            written = 0
            for _ in range(start_frame, end_frame):
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
                written += 1

            out.release()
            cap.release()

            # Convert to web-compatible H.264 using FFmpeg
            temp_path = out_path + ".temp.mp4"
            if os.path.exists(out_path):
                os.rename(out_path, temp_path)
                cmd = [
                    "ffmpeg", "-y", "-i", temp_path,
                    "-vcodec", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-loglevel", "quiet",
                    out_path
                ]
                subprocess.run(cmd, check=True)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                logger.info(f"Background Encoder: Web-compatible H.264 clip created successfully at: {out_path} ({written} frames)")
        except Exception as e:
            logger.error(f"Background Encoder Error for event {event_id}: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                if not os.path.exists(out_path):
                    os.rename(temp_path, out_path)
                else:
                    os.remove(temp_path)
