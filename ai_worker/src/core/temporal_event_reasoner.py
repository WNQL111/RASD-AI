import time
import logging
from collections import deque
from typing import Dict, List, Optional, Tuple
from core.scene_types import SceneProfile
from core.interaction_types import InteractionPair
from core.event_reasoning_types import (
    EventReasoningState, EventParticipants, EventLifecycleState, EventEvidenceVector
)
from core.false_positive_firewall import FalsePositiveFirewall
from core.multi_signal_evidence_fusion import MultiSignalEvidenceFusionEngine
from core.event_lifecycle_engine import EventLifecycleMachine

logger = logging.getLogger(__name__)

class TemporalEventReasoner:
    """
    Temporal Event Reasoner for ASIS-V2.
    Maintains bounded temporal evidence histories per active event hypothesis.
    Protects against memory leaks via TTL pruning and maximum history caps.
    Includes occlusion grace period handling (15 frames).
    """
    def __init__(self, max_events: int = 20, max_history_frames: int = 300, ttl_seconds: float = 30.0):
        self.max_events = max_events
        self.max_history_frames = max_history_frames
        self.ttl_seconds = ttl_seconds
        
        self.firewall = FalsePositiveFirewall()
        self.fusion_engine = MultiSignalEvidenceFusionEngine()
        self.lifecycle_machine = EventLifecycleMachine()

        # Bounded event states lookup: event_key -> EventReasoningState
        self.active_events: Dict[Tuple[int, int], EventReasoningState] = {}
        self.event_histories: Dict[Tuple[int, int], deque] = {}
        self.occlusion_grace: Dict[Tuple[int, int], int] = {}

    def process_pair_event(
        self,
        pair: InteractionPair,
        scene_profile: SceneProfile,
        frame_idx: int
    ) -> EventReasoningState:
        """
        Evaluates an interaction pair over time and returns the updated EventReasoningState.
        """
        pair_key = (min(pair.track_id_a, pair.track_id_b), max(pair.track_id_a, pair.track_id_b))

        # Memory Budget Protection: Prune stale events if capacity exceeded
        if len(self.active_events) >= self.max_events and pair_key not in self.active_events:
            self._prune_oldest_events()

        if pair_key not in self.active_events:
            event_id = f"evt_{pair_key[0]}_{pair_key[1]}_{frame_idx}"
            participants = EventParticipants(
                track_ids=[pair.track_id_a, pair.track_id_b],
                primary_track_a=pair.track_id_a,
                primary_track_b=pair.track_id_b,
                participant_count=2
            )
            self.active_events[pair_key] = EventReasoningState(
                event_id=event_id,
                participants=participants,
                start_frame=frame_idx
            )
            self.event_histories[pair_key] = deque(maxlen=self.max_history_frames)

        state = self.active_events[pair_key]
        history = self.event_histories[pair_key]

        history.append((frame_idx, pair.risk_score, pair.approach_score))
        persistence_frames = len(history)

        # 1. False Positive Firewall
        fw_decision, contradiction_score, contradiction_reasons = self.firewall.evaluate_hypothesis(
            pair, scene_profile, persistence_frames
        )
        state.firewall_decision = fw_decision

        # 2. Multi-Signal Evidence Fusion
        evidence_vec, explain_codes = self.fusion_engine.fuse_signals(
            pair, scene_profile, persistence_frames, contradiction_score, contradiction_reasons
        )
        state.evidence_vector = evidence_vec
        state.explainability_reasons = explain_codes

        # 3. Deterministic Event Lifecycle Machine Transition
        state = self.lifecycle_machine.evaluate_transition(state, fw_decision, evidence_vec, frame_idx)

        # Reset occlusion grace period on active match
        self.occlusion_grace[pair_key] = 0

        return state

    def handle_occlusion_grace_period(self, active_pair_keys: set, frame_idx: int):
        """
        Grants a 15-frame grace period for temporary track occlusions before removing state.
        """
        stale_keys = [k for k in self.active_events if k not in active_pair_keys]
        for k in stale_keys:
            grace = self.occlusion_grace.get(k, 0) + 1
            self.occlusion_grace[k] = grace
            if grace > 15: # Grace period expired
                state = self.active_events[k]
                state.current_lifecycle_state = EventLifecycleState.ENDED
                self.active_events.pop(k, None)
                self.event_histories.pop(k, None)
                self.occlusion_grace.pop(k, None)

    def _prune_oldest_events(self):
        now = time.time()
        stale = [
            k for k, state in self.active_events.items()
            if (now - state.last_updated) > self.ttl_seconds or state.current_lifecycle_state == EventLifecycleState.NONE
        ]
        for k in stale:
            self.active_events.pop(k, None)
            self.event_histories.pop(k, None)
            self.occlusion_grace.pop(k, None)
