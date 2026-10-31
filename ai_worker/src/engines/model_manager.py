import os
import logging
from ultralytics import YOLO, RTDETR
from detectors.registry import PortableObjectRegistry
from core.device_manager import device_manager

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Decoupled Centralized Model Manager with Shared VRAM Cache Pool.
    Dynamically loads, shares, and hot-reloads YOLOv8 (yolov8n.pt, yolov8m.pt) or RT-DETR models.
    Binds all model instances exclusively to the hardware device provided by DeviceManager.
    Reuses PyTorch GPU model instances across stream pipelines to prevent VRAM bloat.
    """
    def __init__(self, model_dir: str = "/app/models", default_model: str = "yolov8n.pt"):
        self.model_dir = model_dir
        self.active_model_name = default_model
        self._model_cache = {}
        self.detector = None
        self.target_classes = [0, 1, 2, 3, 5, 7] + PortableObjectRegistry.get_registered_classes()
        self.load_model(default_model)

    def get_or_load_model_instance(self, model_name: str):
        """Retrieves PyTorch model instance from cache or loads it once on CUDA GPU."""
        if model_name in self._model_cache:
            return self._model_cache[model_name]

        candidates = [
            os.path.join(self.model_dir, model_name),
            os.path.join("models", model_name),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models", model_name),
            model_name
        ]
        resolved_path = model_name
        for c in candidates:
            if c and os.path.exists(c):
                resolved_path = c
                break

        target_device = device_manager.get_device()
        logger.info(f"ModelManager: Loading new model instance '{model_name}' ({resolved_path}) on device '{device_manager.get_device_str()}'")
        
        try:
            if "rtdetr" in model_name.lower():
                instance = RTDETR(resolved_path)
            else:
                instance = YOLO(resolved_path)
            
            try:
                instance.to(target_device)
            except Exception as dev_err:
                logger.warning(f"ModelManager: Could not explicitly move model {model_name} to {target_device}: {dev_err}")

            device_manager.warmup_model(instance)
            self._model_cache[model_name] = instance
            logger.info(f"ModelManager: Model '{model_name}' loaded, warmed up, and cached in VRAM pool.")
            return instance
        except Exception as e:
            logger.error(f"ModelManager: Failed to load model {model_name}: {e}")
            if model_name != "yolov8n.pt":
                logger.warning("ModelManager: Fallback to default 'yolov8n.pt'")
                return self.get_or_load_model_instance("yolov8n.pt")
            return None

    def load_model(self, model_name: str):
        """Switches active detector instance instantly from VRAM cache pool."""
        self.active_model_name = model_name
        self.detector = self.get_or_load_model_instance(model_name)

    def detect(self, frame, model_name: str = None):
        """Standardized inference method with optional per-camera model routing."""
        target_detector = self.detector
        if model_name and model_name != self.active_model_name:
            target_detector = self.get_or_load_model_instance(model_name)
            
        if not target_detector:
            return []
            
        try:
            with device_manager.get_inference_context():
                results = target_detector(
                    frame,
                    classes=self.target_classes,
                    verbose=False,
                    device=device_manager.get_device()
                )
            return results
        except Exception as e:
            logger.error(f"ModelManager: Error during inference: {e}")
            return []
