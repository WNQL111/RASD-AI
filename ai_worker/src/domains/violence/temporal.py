# Violence Domain Temporal Persistence Engine
import uuid
import time
from collections import defaultdict
from typing import Dict, Tuple, Optional

class ViolenceTemporalTracker:
    def __init__(self, duration_thresh: int = 30, max_ttl_seconds: float = 300.0):
        self.duration_thresh = duration_thresh
        self.max_ttl_seconds = max_ttl_seconds
        self.state_acc: Dict[Tuple[int, int], int] = defaultdict(int)
        self.episode_ids: Dict[Tuple[int, int], str] = {}
        self.last_seen: Dict[Tuple[int, int], float] = {}

    def get_episode_id(self, pair_key: Tuple[int, int]) -> str:
        if pair_key not in self.episode_ids:
            self.episode_ids[pair_key] = str(uuid.uuid4())
        return self.episode_ids[pair_key]

    def update_pair(self, pair_key: Tuple[int, int], active: bool) -> int:
        now = time.time()
        self.last_seen[pair_key] = now
        
        if active:
            self.state_acc[pair_key] += 1
        else:
            if pair_key in self.state_acc:
                self.state_acc[pair_key] = max(0, self.state_acc[pair_key] - 1)
            
        current_val = self.state_acc.get(pair_key, 0)
        if current_val == 0:
            self.state_acc.pop(pair_key, None)
            self.episode_ids.pop(pair_key, None)

        self.cleanup_expired_keys(now)
        return current_val

    def cleanup_expired_keys(self, current_time: float):
        expired = [k for k, last in self.last_seen.items() if (current_time - last) > self.max_ttl_seconds or self.state_acc.get(k, 0) == 0]
        for k in expired:
            self.state_acc.pop(k, None)
            self.episode_ids.pop(k, None)
            self.last_seen.pop(k, None)

