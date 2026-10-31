import logging
from typing import Dict, Optional, Tuple
from core.event_reasoning_types import (
    EventLifecycleState, FirewallDecision, EventReasoningState, EventEvidenceVector
)

logger = logging.getLogger(__name__)

class EventLifecycleMachine:
    """
    Event Lifecycle Machine for ASIS-V2.
    Manages deterministic state transitions (NONE -> SUSPECTED -> CANDIDATE -> CONFIRMED -> ACTIVE -> ENDING -> ENDED -> COOLDOWN).
    Applies Hysteresis (Enter=0.55, Exit=0.25) and prevents alert storms.
    """
    def __init__(self, enter_thresh: float = 0.55, exit_thresh: float = 0.25, cooldown_frames: int = 30):
        self.enter_thresh = enter_thresh
        self.exit_thresh = exit_thresh
        self.cooldown_frames = cooldown_frames

    def evaluate_transition(
        self,
        current_state: EventReasoningState,
        firewall_decision: str,
        evidence_vector: EventEvidenceVector,
        frame_idx: int
    ) -> EventReasoningState:
        """
        Evaluates state transition based on firewall decision and net evidence score.
        """
        net_score = evidence_vector.net_evidence_score
        curr = current_state.current_lifecycle_state

        # Cooldown state countdown
        if curr == EventLifecycleState.COOLDOWN:
            current_state.cooldown_frames_remaining -= 1
            if current_state.cooldown_frames_remaining <= 0:
                current_state.current_lifecycle_state = EventLifecycleState.NONE
            return current_state

        # Firewall Suppression Rule Override
        if firewall_decision == FirewallDecision.SUPPRESS:
            if curr in [EventLifecycleState.CONFIRMED, EventLifecycleState.ACTIVE]:
                current_state.current_lifecycle_state = EventLifecycleState.ENDING
            elif curr in [EventLifecycleState.SUSPECTED, EventLifecycleState.CANDIDATE]:
                current_state.current_lifecycle_state = EventLifecycleState.REJECTED
            return current_state

        # Normal Hysteresis State Machine
        if curr in [EventLifecycleState.NONE, EventLifecycleState.REJECTED]:
            if net_score >= 0.30:
                current_state.current_lifecycle_state = EventLifecycleState.SUSPECTED

        elif curr == EventLifecycleState.SUSPECTED:
            if net_score >= self.enter_thresh:
                current_state.current_lifecycle_state = EventLifecycleState.CANDIDATE
            elif net_score < 0.20:
                current_state.current_lifecycle_state = EventLifecycleState.NONE

        elif curr == EventLifecycleState.CANDIDATE:
            if net_score >= self.enter_thresh and firewall_decision == FirewallDecision.PASS:
                current_state.current_lifecycle_state = EventLifecycleState.CONFIRMED
            elif net_score < 0.25:
                current_state.current_lifecycle_state = EventLifecycleState.REJECTED

        elif curr == EventLifecycleState.CONFIRMED:
            current_state.current_lifecycle_state = EventLifecycleState.ACTIVE

        elif curr == EventLifecycleState.ACTIVE:
            if net_score < self.exit_thresh:
                current_state.current_lifecycle_state = EventLifecycleState.ENDING

        elif curr == EventLifecycleState.ENDING:
            if net_score < self.exit_thresh:
                current_state.current_lifecycle_state = EventLifecycleState.ENDED
                current_state.cooldown_frames_remaining = self.cooldown_frames
            elif net_score >= self.enter_thresh:
                current_state.current_lifecycle_state = EventLifecycleState.ACTIVE

        elif curr == EventLifecycleState.ENDED:
            current_state.current_lifecycle_state = EventLifecycleState.COOLDOWN
            current_state.cooldown_frames_remaining = self.cooldown_frames

        current_state.last_seen_frame = frame_idx
        return current_state
