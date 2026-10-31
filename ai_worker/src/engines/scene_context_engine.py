import logging

logger = logging.getLogger(__name__)

class SceneContextEngine:
    """
    Dynamically scales AI rule thresholds based on camera operational environments
    (Mall, Airport, Office, Parking, Classroom, Mosque, Hospital, Road).
    """
    def __init__(self, scene_type="Mall"):
        self.scene_type = scene_type or "Mall"

    def adjust_thresholds(self, base_rules):
        """
        Applies context multipliers to base rules.
        Returns a dict of adjusted rule values.
        """
        rules = base_rules.copy()
        
        # Default multipliers
        multipliers = {
            "violence_velocity_thresh": 1.0,
            "violence_proximity_thresh": 1.0,
            "crowd_density_thresh": 1.0,
            "theft_flee_velocity_thresh": 1.0,
        }

        s_type = self.scene_type.lower()
        if s_type == "office" or s_type == "classroom":
            multipliers["violence_velocity_thresh"] = 0.7
            multipliers["theft_flee_velocity_thresh"] = 0.7
            multipliers["crowd_density_thresh"] = 0.5
        elif s_type == "mosque" or s_type == "mall" or s_type == "airport":
            multipliers["crowd_density_thresh"] = 2.0
            multipliers["violence_proximity_thresh"] = 0.8
        elif s_type == "parking" or s_type == "road":
            multipliers["violence_velocity_thresh"] = 1.4
            multipliers["theft_flee_velocity_thresh"] = 1.3
            multipliers["crowd_density_thresh"] = 0.6
        elif s_type == "hospital":
            multipliers["violence_velocity_thresh"] = 0.6
            multipliers["crowd_density_thresh"] = 0.7

        # Apply multipliers
        for key, mult in multipliers.items():
            if key in rules:
                try:
                    rules[key] = float(rules[key]) * mult
                except (ValueError, TypeError):
                    pass

        return rules
