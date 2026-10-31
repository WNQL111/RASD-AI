import logging
from typing import Dict, Any, Tuple
from core.scene_types import (
    SceneState, AnalysisMode, SceneProfile, AdaptiveAnalysisProfile, CameraMotionClass
)

logger = logging.getLogger(__name__)

class SceneStateMachine:
    """
    Deterministic Scene State Machine for ASIS-V2.
    Manages composite scene state transitions: STABLE -> ACTIVE -> SUSPICIOUS -> HIGH_RISK -> EVENT_CONFIRMED -> COOLDOWN.
    Calculates analysis_pressure (composite risk) and maps state -> AdaptiveAnalysisProfile.
    Includes Hysteresis Cooldown on de-escalation to prevent tier oscillation.
    """
    def __init__(self, hysteresis_frames: int = 15):
        self.current_state: str = SceneState.STABLE
        self.hysteresis_frames = hysteresis_frames
        self.cooldown_counter = 0
        self.metrics = {
            "state_transitions_count": 0,
            "escalations_count": 0,
            "de_escalations_count": 0
        }

    def evaluate(
        self,
        scene_profile: SceneProfile,
        max_normalized_vel: float = 0.0,
        evidence_score: float = 0.0,
        baseline_ctx: Any = None,
        suppression_info: Any = None
    ) -> Tuple[str, AdaptiveAnalysisProfile]:
        """
        Evaluates composite scene signals and updates current_state and AdaptiveAnalysisProfile.
        Ensures crowd density and track count trigger CROWD_MODE, NOT direct violence risk.
        """
        # 1. Compute Composite Risk (Analysis Pressure based on genuine motion & evidence, NOT crowd count)
        motion_factor = min(1.0, max_normalized_vel / 5.0)

        # Scale down motion influence if camera is shaking/panning
        if scene_profile.global_motion_class in [CameraMotionClass.SHAKE, CameraMotionClass.PAN]:
            motion_factor *= 0.4

        suppression_discount = suppression_info.get("suppression_score", 0.0) if suppression_info else 0.0

        analysis_pressure = round(
            max(0.0, (0.50 * motion_factor) + (0.50 * evidence_score) - (0.30 * suppression_discount)),
            3
        )

        # 2. Target State Determination based on Analysis Pressure & Evidence
        target_state = SceneState.STABLE

        if evidence_score >= 0.70:
            target_state = SceneState.EVENT_CONFIRMED
        elif evidence_score >= 0.40 or analysis_pressure >= 0.65:
            target_state = SceneState.HIGH_RISK
        elif analysis_pressure >= 0.35:
            target_state = SceneState.SUSPICIOUS
        elif scene_profile.people_count >= 10 or scene_profile.crowd_density > 0.30:
            target_state = SceneState.CROWDED
        elif scene_profile.people_count > 0 or max_normalized_vel > 0.5:
            target_state = SceneState.ACTIVE
        else:
            target_state = SceneState.STABLE

        # 3. Escalation vs Hysteresis De-escalation
        state_order = [
            SceneState.STABLE, SceneState.ACTIVE, SceneState.CROWDED,
            SceneState.SUSPICIOUS, SceneState.HIGH_RISK, SceneState.EVENT_CANDIDATE,
            SceneState.EVENT_CONFIRMED
        ]

        target_idx = state_order.index(target_state) if target_state in state_order else 0
        current_idx = state_order.index(self.current_state) if self.current_state in state_order else 0

        if target_idx > current_idx:
            # Fast Escalation
            logger.info(f"SceneStateMachine: Escalating {self.current_state} -> {target_state} (Pressure: {analysis_pressure})")
            self.current_state = target_state
            self.cooldown_counter = self.hysteresis_frames
            self.metrics["escalations_count"] += 1
            self.metrics["state_transitions_count"] += 1
        elif target_idx < current_idx:
            # Hysteresis De-escalation
            if self.cooldown_counter > 0:
                self.cooldown_counter -= 1
                # Retain current higher state during cooldown
            else:
                logger.info(f"SceneStateMachine: De-escalating {self.current_state} -> {target_state}")
                self.current_state = target_state
                self.metrics["de_escalations_count"] += 1
                self.metrics["state_transitions_count"] += 1

        # 4. Map SceneState -> AdaptiveAnalysisProfile
        profile = self._map_state_to_profile(self.current_state, analysis_pressure)
        return self.current_state, profile

    def _map_state_to_profile(self, state: str, pressure: float) -> AdaptiveAnalysisProfile:
        if state == SceneState.STABLE:
            return AdaptiveAnalysisProfile(
                mode=AnalysisMode.LIGHT,
                target_fps=8,
                input_resolution=640,
                run_pose=False,
                run_refinement=False,
                reason=f"stable_scene_pressure_{pressure}"
            )
        elif state in [SceneState.ACTIVE, SceneState.CROWDED]:
            return AdaptiveAnalysisProfile(
                mode=AnalysisMode.STANDARD,
                target_fps=15 if state == SceneState.ACTIVE else 20,
                input_resolution=640,
                run_pose=False,
                run_refinement=False,
                reason=f"active_crowded_scene_pressure_{pressure}"
            )
        elif state == SceneState.SUSPICIOUS:
            return AdaptiveAnalysisProfile(
                mode=AnalysisMode.FOCUSED,
                target_fps=25,
                input_resolution=640,
                run_pose=False,
                run_refinement=False,
                reason=f"suspicious_interaction_pressure_{pressure}"
            )
        elif state in [SceneState.HIGH_RISK, SceneState.EVENT_CANDIDATE]:
            return AdaptiveAnalysisProfile(
                mode=AnalysisMode.DEEP,
                target_fps=25,
                input_resolution=640,
                run_pose=True,
                run_refinement=False,
                deep_analysis_enabled=True,
                reason=f"high_risk_deep_analysis_pressure_{pressure}"
            )
        else: # EVENT_CONFIRMED
            return AdaptiveAnalysisProfile(
                mode=AnalysisMode.CRITICAL,
                target_fps=25,
                input_resolution=640,
                run_pose=True,
                run_refinement=True,
                deep_analysis_enabled=True,
                reason=f"event_confirmed_critical_profile_pressure_{pressure}"
            )
