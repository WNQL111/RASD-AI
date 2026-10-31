import logging
import time
from typing import Optional, Dict, Any
from core.routing_types import RoutingContext, RoutingDecision, ModelTier
from core.routing_policy import RoutingPolicy
from core.device_manager import device_manager

logger = logging.getLogger(__name__)

class ModelRouter:
    """
    Independent Adaptive Model Router for ASIS-V2.
    Decides the optimal pretrained model, tier, and inference policy based on RoutingContext.
    Does NOT execute model inference itself (delegates serving to ModelManager).
    Guarantees fail-safe fallback and hysteresis between model tier transitions.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ModelRouter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, enabled: bool = True):
        if self._initialized:
            return
        self._initialized = True
        self.enabled = enabled
        self.policy = RoutingPolicy()
        self.last_decision: Optional[RoutingDecision] = None
        self.hysteresis_counter = 0
        self.metrics = {
            "decisions_count": 0,
            "fast_tier_count": 0,
            "balanced_tier_count": 0,
            "high_accuracy_tier_count": 0,
            "pose_triggered_count": 0,
            "fallback_applied_count": 0,
            "oom_prevented_count": 0,
            "router_exceptions_count": 0
        }
        logger.info("ModelRouter initialized successfully.")

    def route_detection(self, context: RoutingContext) -> RoutingDecision:
        return self.select_model(context)

    def select_model(self, context: RoutingContext) -> RoutingDecision:
        """
        Main entry point: Evaluates RoutingContext and returns a RoutingDecision.
        Wrapped in fail-safe try-except to ensure current pipeline NEVER crashes.
        """
        self.metrics["decisions_count"] += 1

        if not self.enabled:
            return self._create_disabled_default_decision()

        try:
            # 1. Populate current live hardware memory metrics if available
            if context.gpu_memory_used_mb <= 0:
                stats = device_manager.get_memory_stats()
                context.gpu_memory_used_mb = stats.get("allocated_mb", 0.0)

            # 2. Evaluate Policy
            decision = self.policy.evaluate(context)

            # 3. Apply Hysteresis to Tier Demotions to prevent oscillation
            if decision.tier != ModelTier.FAST:
                self.hysteresis_counter = 15

            if self.last_decision and self.last_decision.tier != decision.tier:
                if self._is_demotion(self.last_decision.tier, decision.tier):
                    if self.hysteresis_counter > 0:
                        self.hysteresis_counter -= 1
                        # Retain previous higher tier decision during hysteresis cooldown
                        decision = self.last_decision
                        decision.reason += "_hysteresis_retained"
                    else:
                        self.hysteresis_counter = 15
                else:
                    self.hysteresis_counter = 15

            # Enforce pose execution if explicitly requested in routing context
            if context.pose_needed:
                decision.run_pose = True

            # 4. Update Metrics
            self._update_metrics(decision)
            self.last_decision = decision

            return decision

        except Exception as e:
            logger.error(f"ModelRouter: Exception during routing decision ({e}). Applying fail-safe fallback.")
            self.metrics["router_exceptions_count"] += 1
            return self._create_fail_safe_fallback_decision(f"exception_{str(e)}")

    def _is_demotion(self, prev_tier: str, new_tier: str) -> bool:
        tier_weights = {ModelTier.FAST: 1, ModelTier.BALANCED: 2, ModelTier.HIGH_ACCURACY: 3, ModelTier.SPECIALIST: 3}
        return tier_weights.get(new_tier, 1) < tier_weights.get(prev_tier, 1)

    def _update_metrics(self, decision: RoutingDecision):
        if decision.tier == ModelTier.FAST:
            self.metrics["fast_tier_count"] += 1
        elif decision.tier == ModelTier.BALANCED:
            self.metrics["balanced_tier_count"] += 1
        elif decision.tier in [ModelTier.HIGH_ACCURACY, ModelTier.SPECIALIST]:
            self.metrics["high_accuracy_tier_count"] += 1

        if decision.run_pose:
            self.metrics["pose_triggered_count"] += 1

        if "fallback" in decision.reason:
            self.metrics["fallback_applied_count"] += 1

        if "resource_constrained" in decision.reason:
            self.metrics["oom_prevented_count"] += 1

    def _create_disabled_default_decision(self) -> RoutingDecision:
        return RoutingDecision(
            selected_model="yolov8n.pt",
            task="object_detection",
            tier=ModelTier.FAST,
            reason="router_disabled_default_path",
            fallback_model="yolov8n.pt",
            target_fps=25,
            run_pose=False
        )

    def _create_fail_safe_fallback_decision(self, reason_detail: str) -> RoutingDecision:
        return RoutingDecision(
            selected_model="yolov8n.pt",
            task="object_detection",
            tier=ModelTier.FAST,
            reason=f"fail_safe_fallback_{reason_detail}",
            fallback_model="yolov8n.pt",
            target_fps=25,
            run_pose=False
        )

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self.metrics)

# Global Singleton Instance
model_router = ModelRouter()
