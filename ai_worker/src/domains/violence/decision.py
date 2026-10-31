# Violence Domain Decision Contract
from typing import Dict, Any, List, Tuple
from .models import ViolenceDecision

class ViolenceDecisionEngine:
    @staticmethod
    def make_decision(pair_key: Tuple[int, int], confidence: float, persistence: int, duration_thresh: int, reasons: List[str]) -> ViolenceDecision:
        if confidence >= 0.65 and persistence >= (duration_thresh // 2):
            state = 'CONFIRMED'
        elif confidence >= 0.40:
            state = 'CANDIDATE'
        else:
            state = 'REJECTED'
            
        return ViolenceDecision(
            state=state,
            confidence=confidence,
            affected_tracks=list(pair_key),
            reason_codes=reasons
        )
