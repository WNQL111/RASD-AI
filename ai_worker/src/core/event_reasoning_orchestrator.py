import logging
from typing import List, Dict, Tuple, Optional
from core.scene_types import SceneProfile
from core.interaction_types import InteractionPair, InteractionEngineResult
from core.event_reasoning_types import EventReasoningState, EventLifecycleState
from core.temporal_event_reasoner import TemporalEventReasoner

logger = logging.getLogger(__name__)

class EventReasoningOrchestrator:
    """
    Master Event Reasoning Orchestrator for ASIS-V2.
    Integrates False Positive Firewall, Temporal Event Reasoner, Multi-Signal Fusion, and Event Lifecycle.
    """
    def __init__(self, max_events: int = 20):
        self.temporal_reasoner = TemporalEventReasoner(max_events=max_events)

    def evaluate_events(
        self,
        interaction_res: InteractionEngineResult,
        scene_profile: SceneProfile,
        frame_idx: int
    ) -> Tuple[List[EventReasoningState], float, List[str]]:
        """
        Evaluates active interaction pairs and returns (evaluated_events, max_net_evidence, explainability_reasons).
        """
        evaluated_events: List[EventReasoningState] = []
        max_net_evidence = 0.0
        all_reasons = []
        active_pair_keys = set()

        for p in interaction_res.active_pairs:
            pair_key = (min(p.track_id_a, p.track_id_b), max(p.track_id_a, p.track_id_b))
            active_pair_keys.add(pair_key)

            ev_state = self.temporal_reasoner.process_pair_event(p, scene_profile, frame_idx)
            evaluated_events.append(ev_state)

            if ev_state.evidence_vector.net_evidence_score > max_net_evidence:
                max_net_evidence = ev_state.evidence_vector.net_evidence_score

            all_reasons.extend(ev_state.explainability_reasons)

        # Handle occlusion grace period for missing tracks
        self.temporal_reasoner.handle_occlusion_grace_period(active_pair_keys, frame_idx)

        return evaluated_events, max_net_evidence, list(set(all_reasons))
