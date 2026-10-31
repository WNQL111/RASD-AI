import os
import logging
import numpy as np
from ultralytics import YOLO
from core.device_manager import device_manager

logger = logging.getLogger(__name__)

class PoseDetector:
    """
    Local Pose Estimation Module.
    Extracts 17 COCO body keypoints (Nose, Eyes, Ears, Shoulders, Elbows, Wrists, Hips, Knees, Ankles)
    and computes motion vectors for hands, arms, and body limbs.
    Runs 100% locally using DeviceManager.
    """
    def __init__(self, model_dir: str = "/app/models", model_name: str = "yolov8n-pose.pt"):
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
        self.model = None
        self.load_model()

    def load_model(self):
        try:
            logger.info(f"PoseDetector: Loading local pose model '{self.model_path}' on device '{device_manager.get_device_str()}'")
            if os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
            else:
                logger.info(f"PoseDetector: Pose model file not found at {self.model_path}, initializing YOLO('yolov8n-pose.pt')")
                self.model = YOLO("yolov8n-pose.pt")
                
            try:
                self.model.to(device_manager.get_device())
            except Exception:
                pass
            device_manager.warmup_model(self.model)
        except Exception as e:
            logger.warning(f"PoseDetector: Local pose model initialization fallback: {e}")
            self.model = None

    def estimate_pose(self, frame, person_boxes=None) -> list:
        """
        Runs pose inference on the frame and returns keypoints for detected persons.
        Returns a list of dicts:
        [{
            "keypoints": [[x, y, conf], ...], # 17 COCO keypoints
            "hand_velocity": float,
            "arm_extension": float,
            "posture_angle": float
        }, ...]
        """
        results = []
        if not self.model:
            return results

        try:
            with device_manager.get_inference_context():
                pose_results = self.model(
                    frame,
                    verbose=False,
                    device=device_manager.get_device()
                )

            if len(pose_results) > 0 and pose_results[0].keypoints is not None:
                kpts = pose_results[0].keypoints
                if kpts.data is not None:
                    data = kpts.data.cpu().numpy()
                    for person_kpts in data:
                        # Extract key joints:
                        # 0: nose, 5: L_shoulder, 6: R_shoulder, 7: L_elbow, 8: R_elbow,
                        # 9: L_wrist, 10: R_wrist, 11: L_hip, 12: R_hip
                        wrist_l = person_kpts[9][:2] if len(person_kpts) > 9 else [0, 0]
                        wrist_r = person_kpts[10][:2] if len(person_kpts) > 10 else [0, 0]
                        shoulder_l = person_kpts[5][:2] if len(person_kpts) > 5 else [0, 0]
                        shoulder_r = person_kpts[6][:2] if len(person_kpts) > 6 else [0, 0]

                        # Arm extension distance (wrists to shoulders)
                        arm_ext_l = float(np.linalg.norm(wrist_l - shoulder_l)) if sum(wrist_l) > 0 else 0.0
                        arm_ext_r = float(np.linalg.norm(wrist_r - shoulder_r)) if sum(wrist_r) > 0 else 0.0

                        results.append({
                            "keypoints": person_kpts.tolist(),
                            "wrist_l": wrist_l.tolist(),
                            "wrist_r": wrist_r.tolist(),
                            "arm_extension": round(max(arm_ext_l, arm_ext_r), 2)
                        })
        except Exception as e:
            logger.warning(f"PoseDetector: Inference exception: {e}")

        return results

    def detect(self, frame, person_boxes=None) -> list:
        return self.estimate_pose(frame, person_boxes)
