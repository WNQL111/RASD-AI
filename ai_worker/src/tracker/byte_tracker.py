import os
import logging
from ultralytics import YOLO, RTDETR
from core.device_manager import device_manager

logger = logging.getLogger(__name__)

class ByteTracker:
    def __init__(self, detector):
        """
        Initializes the ByteTracker wrapper.
        Each ByteTracker maintains its own private YOLO/RTDETR instance to prevent
        shape mismatches during concurrent multi-stream tracking.
        Binds exclusively to the hardware device managed by DeviceManager.
        """
        self.detector = detector
        detector_path = getattr(detector, 'model_path', None)
        candidates = [
            detector_path,
            os.path.join("models", "yolov8n.pt"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models", "yolov8n.pt"),
            "/app/models/yolov8n.pt",
            "yolov8n.pt"
        ]
        resolved_path = "yolov8n.pt"
        for c in candidates:
            if c and os.path.exists(c):
                resolved_path = c
                break
        self.model_path = resolved_path
        logger.info(f"ByteTracker: Initializing private model tracker on '{device_manager.get_device_str()}' for {self.model_path}")
        self.model = YOLO(self.model_path)
        try:
            self.model.to(device_manager.get_device())
        except Exception:
            pass

    def update(self, *args, **kwargs):
        """
        Runs detection and tracking on a single frame.
        Assures isolated tracking state per stream using DeviceManager device.
        Supports both update(frame, active_model=None) and update(raw_detections, frame, active_model=None).
        """
        import numpy as np
        frame = None
        active_model = kwargs.get('active_model', None)
        
        if len(args) == 1:
            frame = args[0]
        elif len(args) >= 2:
            if isinstance(args[0], (list, tuple)) and isinstance(args[1], np.ndarray):
                frame = args[1]
                if len(args) > 2:
                    active_model = args[2]
            elif isinstance(args[0], np.ndarray):
                frame = args[0]
                if not isinstance(args[1], np.ndarray):
                    active_model = args[1]
            else:
                frame = args[1] if isinstance(args[1], np.ndarray) else args[0]
        
        if frame is None:
            return []

        # Cache loaded models to avoid re-instantiating from disk on every frame
        if not hasattr(self, '_model_cache'):
            self._model_cache = {self.model_path: self.model}

        if active_model is not None and not isinstance(active_model, np.ndarray):
            active_path = getattr(active_model, 'ckpt_path', None)
            if not active_path and hasattr(active_model, 'overrides'):
                active_path = active_model.overrides.get('model')
                
            if active_path and self.model_path != active_path:
                if active_path not in self._model_cache:
                    logger.info(f"ByteTracker: Caching new tracker model from {active_path}")
                    if "rtdetr" in str(active_path).lower() or "rtdetr" in str(type(active_model)).lower():
                        new_model = RTDETR(active_path)
                    else:
                        new_model = YOLO(active_path)
                    try:
                        new_model.to(device_manager.get_device())
                    except Exception:
                        pass
                    self._model_cache[active_path] = new_model

                self.model_path = active_path
                self.model = self._model_cache[active_path]

        target_classes = [0, 1, 2, 3, 5, 7]
        if hasattr(self.detector, 'target_classes'):
            target_classes = self.detector.target_classes
            
        with device_manager.get_inference_context():
            results = self.model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=target_classes,
                verbose=False,
                imgsz=480,
                device=device_manager.get_device()
            )
        
        tracked_objects = []
        
        if len(results) > 0:
            result = results[0]
            boxes = result.boxes
            
            if boxes is not None and boxes.id is not None:
                track_ids = boxes.id.int().cpu().tolist()
                cls_ids = boxes.cls.int().cpu().tolist()
                confidences = boxes.conf.float().cpu().tolist()
                xyxys = boxes.xyxy.cpu().tolist()
                
                for t_id, cls_id, conf, xyxy in zip(track_ids, cls_ids, confidences, xyxys):
                    tracked_objects.append({
                        "track_id": t_id,
                        "class_id": cls_id,
                        "confidence": conf,
                        "bbox": xyxy  # [x1, y1, x2, y2]
                    })
                    
        return tracked_objects
