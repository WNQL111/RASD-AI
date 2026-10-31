import time
import uuid
from typing import Dict, Tuple, Optional, Any
from .config import CollisionConfig
from .contracts import CollisionType, CollisionState, CollisionEvidenceDTO, CollisionDecisionDTO

class CollisionTemporalTracker:
    def __init__(self, config: Optional[CollisionConfig] = None):
        self.config = config or CollisionConfig()
        self.state_acc: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self.confirmed_episodes: Dict[Tuple[int, int], Dict[str, Any]] = {}

    def update(
        self,
        pair_key: Tuple[int, int],
        evidence: CollisionEvidenceDTO,
        frame_idx: int,
        timestamp: Optional[float] = None
    ) -> CollisionDecisionDTO:
        ts = timestamp or time.time()
        c_type = evidence.collision_type
        conf = evidence.final_confidence

        if pair_key not in self.state_acc:
            self.state_acc[pair_key] = {
                'state': CollisionState.MONITORING,
                'persistence': 0,
                'decay_counter': 0,
                'first_seen': ts,
                'last_updated': ts,
                'peak_confidence': conf,
                'episode_id': None,
                'event_id': None,
                'collision_type': c_type
            }

        rec = self.state_acc[pair_key]
        rec['last_updated'] = ts
        rec['peak_confidence'] = max(rec['peak_confidence'], conf)

        if conf >= self.config.MIN_CANDIDATE_CONFIDENCE:
            rec['persistence'] += 1
            rec['decay_counter'] = 0

            if rec['state'] == CollisionState.MONITORING and rec['persistence'] >= 2:
                rec['state'] = CollisionState.CANDIDATE
            elif rec['state'] == CollisionState.CANDIDATE and rec['persistence'] >= 4:
                rec['state'] = CollisionState.INVESTIGATING
            elif rec['state'] == CollisionState.INVESTIGATING and rec['persistence'] >= 6:
                rec['state'] = CollisionState.SUPPORTED

            if (rec['persistence'] >= self.config.COLLISION_MIN_PERSISTENCE and conf >= self.config.CONFIRMATION_THRESHOLD) or (evidence.deceleration_evidence >= 0.18 and evidence.overlap_evidence >= 0.25 and rec['persistence'] >= 2):
                if rec['state'] != CollisionState.CONFIRMED:
                    rec['state'] = CollisionState.CONFIRMED
                    if not rec['episode_id']:
                        rec['episode_id'] = str(uuid.uuid4())
                        rec['event_id'] = str(uuid.uuid4())
                        self.confirmed_episodes[pair_key] = {
                            'episode_id': rec['episode_id'],
                            'event_id': rec['event_id'],
                            'confirmed_at': ts
                        }
        else:
            rec['decay_counter'] += 1
            if rec['decay_counter'] >= self.config.HYSTERESIS_DECAY_FRAMES:
                if rec['state'] == CollisionState.CONFIRMED:
                    rec['state'] = CollisionState.CLOSED
                else:
                    rec['state'] = CollisionState.REJECTED
                rec['persistence'] = max(0, rec['persistence'] - 1)

        explainability = {
            'label': f'COLLISION_{c_type.value}',
            'confidence': f'{int(conf * 100)}%',
            'persistence': rec['persistence'],
            'evidence_quality': evidence.quality,
            'base_score': evidence.base_score,
            'suppression_discount': evidence.suppression_discount,
            'reasons': evidence.reason_codes
        }

        return CollisionDecisionDTO(
            pair_key=pair_key,
            collision_type=c_type,
            state=rec['state'],
            confidence=round(conf, 3),
            persistence_count=rec['persistence'],
            episode_id=rec['episode_id'],
            event_id=rec['event_id'],
            reason_codes=evidence.reason_codes,
            explainability=explainability
        )

    def cleanup_expired_keys(self, current_time: Optional[float] = None) -> int:
        now = current_time or time.time()
        ttl = self.config.MEMORY_TTL_SECONDS
        expired = [
            k for k, v in self.state_acc.items()
            if now - v.get('last_updated', now) > ttl
        ]
        for k in expired:
            del self.state_acc[k]
            if k in self.confirmed_episodes:
                del self.confirmed_episodes[k]
        return len(expired)
