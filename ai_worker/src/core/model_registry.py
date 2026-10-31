import os
import time
import logging
from typing import Dict, List, Optional
from core.routing_types import ModelSpec, ModelTask, ModelTier, ModelStatus, LatencyStatus

logger = logging.getLogger(__name__)

class ModelRegistry:
    """
    Centralized Model Capability Registry for ASIS-V2.
    Decouples task declaration from specific model weight files.
    Tracks model specs, status, latencies (measured vs estimated), and fallback availability.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ModelRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_dir: str = "/app/models"):
        if self._initialized:
            return
        self._initialized = True
        self.model_dir = model_dir
        self.registry: Dict[str, ModelSpec] = {}
        self._register_default_models()

    def _register_default_models(self):
        """Registers default pretrained models known to the system."""
        # Tier A: FAST
        self.register_model(ModelSpec(
            model_id="yolov8n.pt",
            path=os.path.join(self.model_dir, "yolov8n.pt"),
            task=ModelTask.OBJECT_DETECTION,
            tier=ModelTier.FAST,
            supported_tasks=[ModelTask.PERSON_DETECTION, ModelTask.OBJECT_DETECTION],
            estimated_vram_mb=350.0,
            expected_latency_ms=6.5,
            latency_status=LatencyStatus.ESTIMATED,
            status=ModelStatus.AVAILABLE,
            priority=10
        ))

        # Tier B: BALANCED
        self.register_model(ModelSpec(
            model_id="yolov8m.pt",
            path=os.path.join(self.model_dir, "yolov8m.pt"),
            task=ModelTask.OBJECT_DETECTION,
            tier=ModelTier.BALANCED,
            supported_tasks=[ModelTask.PERSON_DETECTION, ModelTask.OBJECT_DETECTION],
            estimated_vram_mb=1100.0,
            expected_latency_ms=17.5,
            latency_status=LatencyStatus.ESTIMATED,
            status=ModelStatus.AVAILABLE,
            priority=20
        ))

        # Tier D: SPECIALIST (Pose)
        self.register_model(ModelSpec(
            model_id="yolov8n-pose.pt",
            path=os.path.join(self.model_dir, "yolov8n-pose.pt"),
            task=ModelTask.POSE_ESTIMATION,
            tier=ModelTier.SPECIALIST,
            supported_tasks=[ModelTask.POSE_ESTIMATION],
            estimated_vram_mb=400.0,
            expected_latency_ms=8.2,
            latency_status=LatencyStatus.ESTIMATED,
            status=ModelStatus.AVAILABLE,
            priority=30
        ))

    def register_model(self, spec: ModelSpec):
        """Registers or updates a ModelSpec entry in the central registry."""
        self.registry[spec.model_id] = spec
        logger.info(f"ModelRegistry: Registered model '{spec.model_id}' (Task: {spec.task}, Tier: {spec.tier})")

    def get_spec(self, model_id: str) -> Optional[ModelSpec]:
        """Retrieves ModelSpec by model_id."""
        return self.registry.get(model_id)

    def get_models_by_task(self, task: str) -> List[ModelSpec]:
        """Returns all registered models supporting a specific task, sorted by priority."""
        matches = [spec for spec in self.registry.values() if task in spec.supported_tasks or spec.task == task]
        return sorted(matches, key=lambda s: s.priority)

    def get_models_by_tier(self, tier: str) -> List[ModelSpec]:
        """Returns all registered models in a given tier."""
        return [spec for spec in self.registry.values() if spec.tier == tier]

    def update_status(self, model_id: str, status: str, error: Optional[str] = None):
        """Updates runtime status of a registered model."""
        spec = self.get_spec(model_id)
        if spec:
            spec.status = status
            if error:
                spec.load_error = error
                spec.last_failure_time = time.time()
            elif status == ModelStatus.READY:
                spec.last_load_time = time.time()

    def update_measured_latency(self, model_id: str, latency_ms: float):
        """Updates measured inference latency from benchmarks."""
        spec = self.get_spec(model_id)
        if spec:
            spec.expected_latency_ms = round(latency_ms, 2)
            spec.latency_status = LatencyStatus.MEASURED

    def list_all(self) -> List[ModelSpec]:
        """Lists all registered ModelSpecs."""
        return list(self.registry.values())

# Global Singleton Instance
model_registry = ModelRegistry()
