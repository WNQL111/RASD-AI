import time
import logging
from core.device_manager import device_manager
from core.resource_types import GpuHealthState, ResourceState

logger = logging.getLogger(__name__)

class GpuHealthMonitor:
    """
    GPU Health & Resource Monitor for ASIS-V2.
    Queries DeviceManager for measured VRAM ratio and GPU memory statistics.
    Classifies GPU health state dynamically (HEALTHY / BUSY / PRESSURED / CRITICAL).
    """
    def __init__(self, busy_thresh: float = 0.60, pressure_thresh: float = 0.75, critical_thresh: float = 0.85):
        self.busy_thresh = busy_thresh
        self.pressure_thresh = pressure_thresh
        self.critical_thresh = critical_thresh

    def sample_resource_state(self, current_queue_depth: int = 0, dropped_count: int = 0) -> ResourceState:
        """
        Samples current measured GPU resource state.
        """
        try:
            mem_stats = device_manager.get_memory_stats()
            vram_ratio = mem_stats.get("ratio", 0.0)
            vram_mb = mem_stats.get("allocated_mb", 0.0)
            device_type = mem_stats.get("device", "CPU")

            if "CPU" in device_type:
                health = GpuHealthState.GPU_HEALTHY
            elif vram_ratio >= self.critical_thresh:
                health = GpuHealthState.GPU_CRITICAL
            elif vram_ratio >= self.pressure_thresh:
                health = GpuHealthState.GPU_PRESSURED
            elif vram_ratio >= self.busy_thresh:
                health = GpuHealthState.GPU_BUSY
            else:
                health = GpuHealthState.GPU_HEALTHY

            return ResourceState(
                gpu_utilization=round(vram_ratio * 100.0, 1),
                gpu_memory_ratio=round(vram_ratio, 3),
                gpu_health=health,
                queue_depth=current_queue_depth,
                frame_backlog=current_queue_depth,
                dropped_frames_count=dropped_count,
                measured_vram_mb=round(vram_mb, 2),
                source="MEASURED" if "CUDA" in device_type else "ESTIMATED"
            )
        except Exception as e:
            logger.warning(f"GpuHealthMonitor: Exception reading GPU stats ({e})")
            return ResourceState(gpu_health=GpuHealthState.GPU_HEALTHY, source="ESTIMATED")
