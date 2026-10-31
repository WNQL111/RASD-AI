import os
import requests
import logging
from typing import Any

logger = logging.getLogger(__name__)

class RuleEngine:
    """
    Dynamically fetches and resolves AI thresholds and rules from the backend database.
    Allows administrators to configure thresholds without modifying Python code.
    """
    def __init__(self):
        self.rules = {}
        self.backend_url = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8001/api")
        self.load_rules()

    def load_rules(self):
        """Fetches active thresholds from backend API or falls back to defaults."""
        try:
            response = requests.get(f"{self.backend_url}/rules", timeout=0.5)
            if response.status_code == 200:
                data = response.json()
                self.rules = {r['key']: r['value'] for r in data}
                logger.info("Successfully fetched rules configuration from Backend API.")
                return
        except Exception:
            pass

        # Static Local Defaults
        self.rules = {
            "violence_proximity_thresh": "350.0",
            "violence_velocity_thresh": "6.0",
            "violence_duration_thresh": "2",
            "theft_proximity_thresh": "100.0",
            "theft_separation_thresh": "200.0",
            "theft_flee_velocity_thresh": "25.0",
            "accident_decel_thresh": "10.0",
            "accident_iou_thresh": "0.08",
            "pre_event_roll": "5.0",
            "post_event_roll": "10.0",
            "portable_objects": '["backpack", "handbag", "suitcase", "laptop", "cell phone", "umbrella", "book", "bottle", "cup", "clock"]'
        }

    def get_float(self, key: str, default: float) -> float:
        try:
            return float(self.rules.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_int(self, key: str, default: int) -> int:
        try:
            return int(self.rules.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_str(self, key: str, default: str) -> str:
        return self.rules.get(key, default)

    def get(self, key: str, default: Any = None) -> Any:
        return self.rules.get(key, default)

    def set(self, key: str, value: Any):
        self.rules[key] = str(value) if not isinstance(value, str) else value

