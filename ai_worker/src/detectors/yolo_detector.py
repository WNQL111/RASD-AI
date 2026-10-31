import os
import logging
from ultralytics import YOLO
from detectors.registry import PortableObjectRegistry

logger = logging.getLogger(__name__)

class YoloDetector:
    def __init__(self, model_dir: str = "/app/models", model_name: str = "yolov8n.pt"):
        candidates = [
            os.path.join(model_dir, model_name),
            os.path.join("models", model_name),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models", model_name),
            model_name
        ]
        resolved_path = model_name
        for c in candidates:
            if os.path.exists(c):
                resolved_path = c
                break
        self.model_path = resolved_path
        logger.info(f"Initializing YOLO Detector with model: {self.model_path}")
        self.model = YOLO(self.model_path)
        
        # Keep person (0), bicycle (1), car (2), motorcycle (3), bus (5), truck (7) + portable objects
        self.target_classes = [0, 1, 2, 3, 5, 7] + PortableObjectRegistry.get_registered_classes()

    def get_model(self) -> YOLO:
        return self.model

    def detect(self, frame):
        """Performs raw object detection without tracking."""
        results = self.model(
            frame,
            classes=self.target_classes,
            verbose=False
        )
        return results
