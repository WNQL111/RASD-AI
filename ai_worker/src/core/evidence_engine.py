import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class EvidenceEngine:
    """
    Deterministic Evidence Accumulation & Decay Engine for ASIS-V2.
    Accumulates evidence confidence scores over time based on persistent abnormal indicators.
    Decays evidence when indicators disappear to prevent false positive latching.
    """
    def __init__(self, accumulation_rate: float = 0.15, decay_rate: float = 0.05, confirmation_thresh: float = 0.70):
        self.accumulation_rate = accumulation_rate
        self.decay_rate = decay_rate
        self.confirmation_thresh = confirmation_thresh
        self.evidence_scores: Dict[str, float] = {} # event_key -> score (0.0 to 1.0)
        self.persistence_counters: Dict[str, int] = {}

    def update_evidence(self, event_key: str, signal_detected: bool, signal_strength: float = 1.0) -> float:
        """
        Updates evidence score for a specific candidate key.
        Returns the updated evidence score (0.0 to 1.0).
        """
        current_score = self.evidence_scores.get(event_key, 0.0)

        if signal_detected:
            # Positive Accumulation
            increment = self.accumulation_rate * min(1.0, max(0.1, signal_strength))
            new_score = min(1.0, current_score + increment)
            self.persistence_counters[event_key] = self.persistence_counters.get(event_key, 0) + 1
        else:
            # Deterministic Decay
            new_score = max(0.0, current_score - self.decay_rate)
            if new_score <= 0.0:
                self.persistence_counters.pop(event_key, None)

        self.evidence_scores[event_key] = round(new_score, 3)
        return self.evidence_scores[event_key]

    def is_confirmed(self, event_key: str) -> bool:
        """Returns True if evidence score has reached confirmation threshold."""
        return self.evidence_scores.get(event_key, 0.0) >= self.confirmation_thresh

    def get_score(self, event_key: str) -> float:
        return self.evidence_scores.get(event_key, 0.0)

    def reset_evidence(self, event_key: str):
        self.evidence_scores.pop(event_key, None)
        self.persistence_counters.pop(event_key, None)
