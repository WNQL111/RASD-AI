import logging

logger = logging.getLogger(__name__)

class UncertaintyEngine:
    """
    Decoupled Uncertainty Engine.
    Determines whether a local AI event is uncertain and deserves external verification.
    Applies cost protection filters to avoid querying Gemini for obvious cases.
    """
    def __init__(self, rule_engine):
        self.rule_engine = rule_engine

    def should_verify(self, risk_score: float) -> bool:
        """
        Evaluate if risk score is inside the uncertainty band.
        Obvious threats (>75%) or clear non-threats (<40%) bypass Gemini.
        Bounds are loaded dynamically from settings.
        """
        # Load cost protection thresholds from database rule thresholds
        min_thresh = self.rule_engine.get_float("external_verification_min_thresh", 40.0)
        max_thresh = self.rule_engine.get_float("external_verification_max_thresh", 75.0)

        # Check if external verification is active
        ai_provider = self.rule_engine.get_str("ai_provider", "Disabled")
        api_key = self.rule_engine.get_str("api_key", "")
        
        if ai_provider == "Disabled" or not api_key:
            return False

        # Apply bounds filter
        if min_thresh <= risk_score <= max_thresh:
            logger.info(f"UncertaintyEngine: Event risk {risk_score}% is inside band [{min_thresh}%, {max_thresh}%]. Gemini query APPROVED.")
            return True
            
        logger.info(f"UncertaintyEngine: Event risk {risk_score}% is outside band [{min_thresh}%, {max_thresh}%]. Gemini query BYPASSED.")
        return False

    def calculate_uncertainty(self, confidence: float, risk_score: float) -> float:
        """
        Computes uncertainty score from 0.0 to 1.0.
        Higher uncertainty means closer to the middle of the band.
        """
        min_thresh = self.rule_engine.get_float("external_verification_min_thresh", 40.0)
        max_thresh = self.rule_engine.get_float("external_verification_max_thresh", 75.0)
        
        center = (min_thresh + max_thresh) / 2.0
        distance_from_center = abs(risk_score - center)
        max_distance = (max_thresh - min_thresh) / 2.0
        
        if max_distance <= 0:
            return 0.0
            
        # Linear scale: 1.0 at center, 0.0 at/beyond bounds
        uncertainty = max(0.0, 1.0 - (distance_from_center / max_distance))
        return round(uncertainty, 2)
