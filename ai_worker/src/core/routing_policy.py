import logging
from core.routing_types import (
    RoutingContext, RoutingDecision, ModelTask, ModelTier, ModelStatus
)
from core.model_registry import model_registry

logger = logging.getLogger(__name__)

class RoutingPolicy:
    """
    Pure Deterministic Policy Engine for Model Routing.
    Maps RoutingContext (scene state, level, risk, VRAM usage, queue depth) -> RoutingDecision.
    Includes hardware resource protection rules (e.g. VRAM ratio limit).
    """
    def __init__(self, max_vram_ratio: float = 0.85, max_queue_depth: int = 32):
        self.max_vram_ratio = max_vram_ratio
        self.max_queue_depth = max_queue_depth

    def evaluate(self, context: RoutingContext) -> RoutingDecision:
        """
        Evaluates context against deterministic policy rules and returns a RoutingDecision.
        """
        # 1. Resource Safety Overrides (VRAM & Queue Protection)
        vram_used_ratio = (context.gpu_memory_used_mb / context.gpu_memory_total_mb) if context.gpu_memory_total_mb > 0 else 0.0
        resource_constrained = (vram_used_ratio > self.max_vram_ratio) or (context.queue_depth > self.max_queue_depth)

        # 2. Base Routing Rules based on Execution Level & Scene Risk
        level = context.current_level
        risk = context.risk_state
        pose_needed = context.pose_needed

        selected_model = "yolov8n.pt"
        selected_tier = ModelTier.FAST
        task = ModelTask.OBJECT_DETECTION
        reason = "normal_screening_baseline"
        target_fps = 25
        run_pose = False
        run_refinement = False
        fallback_model = "yolov8n.pt"

        if level == "LEVEL_0_SCREENING":
            selected_model = "yolov8n.pt"
            selected_tier = ModelTier.FAST
            reason = "level0_screening_fast_tier"
            target_fps = 8
            run_pose = False

        elif level == "LEVEL_1_DETECTION":
            selected_model = "yolov8n.pt"
            selected_tier = ModelTier.FAST
            reason = "level1_detection_fast_tier"
            target_fps = 15
            run_pose = False

        elif level == "LEVEL_2_INTERACTION":
            selected_model = "yolov8n.pt"
            selected_tier = ModelTier.FAST
            reason = f"level2_interaction_tracking_{context.track_count}_tracks"
            target_fps = 20
            run_pose = False

        elif level in ["LEVEL_3_FORENSIC", "LEVEL_4_EVIDENCE"] or risk in ["HIGH", "CRITICAL"]:
            # Check if BALANCED model (yolov8m.pt) is requested and VRAM allows it
            if resource_constrained:
                selected_model = "yolov8n.pt"
                selected_tier = ModelTier.FAST
                reason = "resource_constrained_vram_limit_downgrade_to_fast"
                fallback_model = "yolov8n.pt"
            else:
                # Check if yolov8m is available in registry
                spec = model_registry.get_spec("yolov8m.pt")
                if spec and spec.status != ModelStatus.UNAVAILABLE:
                    selected_model = "yolov8m.pt"
                    selected_tier = ModelTier.BALANCED
                    reason = "level3_forensic_high_risk_balanced_tier"
                    fallback_model = "yolov8n.pt"
                    run_refinement = True
                else:
                    selected_model = "yolov8n.pt"
                    selected_tier = ModelTier.FAST
                    reason = "yolov8m_unavailable_fallback_to_fast"

        # Selective Pose determination: Pose runs ONLY if explicitly requested and risk is genuine HIGH/CRITICAL
        run_pose = bool(context.pose_needed and (level in ["LEVEL_3_FORENSIC", "LEVEL_4_EVIDENCE"] or risk in ["HIGH", "CRITICAL"]))

        # Fallback verification: Ensure selected model is registered and available
        spec = model_registry.get_spec(selected_model)
        if not spec or spec.status == ModelStatus.UNAVAILABLE:
            logger.warning(f"RoutingPolicy: Selected model '{selected_model}' unavailable. Falling back to default 'yolov8n.pt'")
            selected_model = fallback_model
            selected_tier = ModelTier.FAST
            reason += "_fallback_applied"

        return RoutingDecision(
            selected_model=selected_model,
            task=task,
            tier=selected_tier,
            reason=reason,
            confidence=1.0,
            fallback_model=fallback_model,
            target_fps=target_fps,
            image_size=640,
            run_pose=run_pose,
            run_refinement=run_refinement,
            priority=10 if selected_tier == ModelTier.FAST else 20
        )
