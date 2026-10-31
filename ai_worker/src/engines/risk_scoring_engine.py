import logging

logger = logging.getLogger(__name__)

class RiskScoringEngine:
    """
    Computes a unified, multi-factor risk score (0-100) combining:
    - Raw AI plugin confidence
    - Zone restrictions
    - Local crowd anomalies (chaotic motions, panicking flow)
    And maps it to Risk Ratings (LOW, MEDIUM, HIGH, CRITICAL) and Escalation Stages.
    """
    def __init__(self):
        pass

    def calculate_risk(self, base_confidence, event_type, crowd_features, matched_zones):
        score = base_confidence * 70.0
        
        zone_impact = 0.0
        for zone in matched_zones:
            z_type = zone.get("type", "").lower()
            if "restricted" in z_type:
                zone_impact += 20.0
            elif "vip" in z_type:
                zone_impact += 15.0
            elif "cashier" in z_type:
                zone_impact += 10.0
            elif "safe" in z_type:
                zone_impact -= 10.0
        score += zone_impact

        crowd_impact = 0.0
        stability = crowd_features.get("stability", 1.0)
        variance = crowd_features.get("variance", 0.0)
        consistency = crowd_features.get("consistency", 1.0)
        
        if event_type == "violence":
            if stability < 0.6:
                crowd_impact += (1.0 - stability) * 15.0
            if consistency < 0.4 and variance > 5.0:
                crowd_impact += 10.0
        elif event_type == "theft":
            if crowd_features.get("interaction_density", 0) > 4:
                crowd_impact += 5.0

        score += crowd_impact
        final_score = max(0.0, min(100.0, score))

        if final_score < 30.0:
            rating = "LOW"
        elif final_score < 60.0:
            rating = "MEDIUM"
        elif final_score < 85.0:
            rating = "HIGH"
        else:
            rating = "CRITICAL"

        if final_score < 40.0:
            stage = "Suspicious"
        elif final_score < 65.0:
            stage = "Possible"
        elif final_score < 80.0:
            stage = "Likely"
        else:
            stage = "Confirmed"

        return {
            "risk_score": round(final_score, 1),
            "risk_rating": rating,
            "escalation_stage": stage,
            "breakdown": {
                "base_confidence_contrib": round(base_confidence * 70.0, 1),
                "zone_impact": round(zone_impact, 1),
                "crowd_impact": round(crowd_impact, 1)
            }
        }
