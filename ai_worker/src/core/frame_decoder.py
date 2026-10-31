import cv2
import logging

logger = logging.getLogger(__name__)

class FrameDecoder:
    """
    Decodes streams or video source files and applies pre-processing.
    Supports dynamic resizing for processing optimization.
    """
    def __init__(self, source_path: str):
        if source_path.startswith("http://") or source_path.startswith("https://") or source_path.startswith("rtsp://"):
            self.cap = cv2.VideoCapture(source_path, cv2.CAP_FFMPEG)
        else:
            self.cap = cv2.VideoCapture(source_path)
        # Set buffer size to 1 to minimize streaming latency on cameras
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def is_opened(self) -> bool:
        return self.cap.isOpened()

    def get_fps(self) -> float:
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        return fps if fps > 0 else 25.0

    def get_frame_count(self) -> int:
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def read_frame(self):
        ret, frame = self.cap.read()
        return ret, frame

    def resize_frame(self, frame, width: int = 416):
        """Downscales frame resolution for fast YOLO CPU execution."""
        h, w = frame.shape[:2]
        if w > width:
            scale = width / w
            new_h = int(h * scale)
            return cv2.resize(frame, (width, new_h))
        return frame

    def release(self):
        self.cap.release()
