import os
import torch
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DeviceManager:
    """
    Universal AI Device Manager.
    Centralized hardware detection and management for PyTorch models.
    Supports CUDA GPU, FP16 mixed precision, Apple MPS, and seamless CPU fallback.
    Prevents application crashes if GPU initialization fails.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DeviceManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.device = self._detect_device()
        self.use_fp16 = self._check_fp16_support()
        logger.info(f"DeviceManager initialized: Primary Device = {self.device}, FP16 Supported = {self.use_fp16}")

    def _detect_device(self) -> torch.device:
        """Determines hardware device following priority: CUDA -> MPS -> CPU."""
        try:
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"DeviceManager: CUDA GPU detected ({device_count} device(s)). Primary GPU: {gpu_name}")
                # Simple CUDA tensor test to verify initialization
                test_tensor = torch.zeros(1, device="cuda:0")
                del test_tensor
                return torch.device("cuda:0")
        except Exception as e:
            logger.warning(f"DeviceManager: CUDA detection failed ({e}). Falling back to next device option.")

        try:
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                logger.info("DeviceManager: Apple MPS detected.")
                return torch.device("mps")
        except Exception as e:
            logger.warning(f"DeviceManager: MPS detection failed ({e}).")

        logger.info("DeviceManager: Using CPU for inference.")
        return torch.device("cpu")

    def _check_fp16_support(self) -> bool:
        """Checks if device supports FP16 mixed precision."""
        if self.device.type == "cuda":
            try:
                capability = torch.cuda.get_device_capability(self.device)
                # Compute capability >= 7.0 (Volta, Turing, Ampere, Ada, Hopper) supports fast FP16
                return capability[0] >= 7
            except Exception:
                return True
        return False

    def get_device(self) -> torch.device:
        """Returns the active PyTorch torch.device object."""
        return self.device

    def get_device_str(self) -> str:
        """Returns human-readable string representation of the active device."""
        if self.device.type == "cuda":
            try:
                gpu_name = torch.cuda.get_device_name(self.device)
                return f"NVIDIA CUDA ({gpu_name})"
            except Exception:
                return "NVIDIA CUDA GPU"
        elif self.device.type == "mps":
            return "Apple MPS GPU"
        return "CPU (High Performance Multi-Threaded)"

    def get_inference_context(self):
        """Returns torch.inference_mode() context manager for optimal execution."""
        return torch.inference_mode()

    def warmup_model(self, model: Any, sample_shape=(1, 3, 640, 640)):
        """Performs initial GPU memory allocation and model warm-up."""
        if self.device.type == "cuda":
            try:
                logger.info(f"DeviceManager: Warming up model on {self.get_device_str()}...")
                dummy_input = torch.zeros(sample_shape, device=self.device)
                if hasattr(model, "predict"):
                    model.predict(dummy_input, verbose=False)
                elif callable(model):
                    model(dummy_input)
                torch.cuda.synchronize()
                logger.info("DeviceManager: GPU Warm-up completed successfully.")
            except Exception as e:
                logger.warning(f"DeviceManager: Model warm-up skipped or failed: {e}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """Returns VRAM and GPU memory stats."""
        stats = {
            "device": self.get_device_str(),
            "is_gpu": self.device.type != "cpu",
            "allocated_mb": 0.0,
            "reserved_mb": 0.0
        }
        if self.device.type == "cuda":
            try:
                stats["allocated_mb"] = round(torch.cuda.memory_allocated(self.device) / (1024 * 1024), 2)
                stats["reserved_mb"] = round(torch.cuda.memory_reserved(self.device) / (1024 * 1024), 2)
            except Exception:
                pass
        return stats

# Global Singleton Instance
device_manager = DeviceManager()
