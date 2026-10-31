import logging
from typing import List, Dict, Tuple, Optional, Any
from core.scene_types import TrackContext, SceneProfile, DistanceClass
from core.interaction_types import (
    InteractionPair, InteractionCluster, InteractionState, InteractionEngineResult
)
from core.pair_candidate_generator import PairCandidateGenerator
from core.spatial_relationship_engine import SpatialRelationshipEngine
from core.approach_separation_engine import ApproachSeparationEngine
from core.direction_analysis_engine import DirectionAnalysisEngine
from core.pose_signal_adapter import PoseSignalAdapter
from core.interaction_graph import InteractionGraph
from core.evidence_engine import EvidenceEngine

logger = logging.getLogger(__name__)

class AdaptiveInteractionEngine:
    """
    Central Adaptive Interaction Intelligence Engine for ASIS-V2.
    Evaluates spatial-temporal relationship dynamics, relative motion, approach/separation,
    heading opposition, selective pose signals, and crowd interaction graphs.
    """
    def __init__(self, proximity_radius_px: float = 180.0, max_pairs: int = 30):
        self.candidate_generator = PairCandidateGenerator(proximity_radius_px=proximity_radius_px, max_pairs=max_pairs)
        self.spatial_engine = SpatialRelationshipEngine()
        self.approach_engine = ApproachSeparationEngine()
        self.direction_engine = DirectionAnalysisEngine()
        self.pose_adapter = PoseSignalAdapter()
        self.graph_engine = InteractionGraph()
        self.evidence_engine = EvidenceEngine()

    def process_interactions(
        self,
        tracks: List[TrackContext],
        frame_idx: int,
        pose_data_map: Optional[Dict[int, List[Any]]] = None
    ) -> InteractionEngineResult:
        """
        Main entry point: Generates pair candidates, analyzes spatial/temporal/motion/pose dynamics,
        builds interaction graph/clusters, and evaluates composite interaction risk.
        """
        # 1. Candidate Generation
        pairs = self.candidate_generator.generate_candidates(tracks)
        track_map = {t.track_id: t for t in tracks}

        max_risk = 0.0
        dominant_state = InteractionState.NONE
        explain_reasons = []
        pose_trigger_needed = False

        active_pair_keys = set()

        for p in pairs:
            active_pair_keys.add((p.track_id_a, p.track_id_b))
            ta = track_map.get(p.track_id_a)
            tb = track_map.get(p.track_id_b)

            if not ta or not tb:
                continue

            # 2. Spatial Relationships
            p = self.spatial_engine.compute_spatial_relation(p, ta, tb)

            # 3. Approach / Separation Derivatives
            p = self.approach_engine.analyze_approach_separation(p, dt_frames=1)

            # 4. Direction & Heading Analysis
            p = self.direction_engine.analyze_directions(p, ta, tb)

            # 5. Pose Signal Feature Extraction (Selective)
            if pose_data_map:
                pa = pose_data_map.get(p.track_id_a)
                pb = pose_data_map.get(p.track_id_b)
                self.pose_adapter.evaluate_pair_pose_anomaly(p, pa, pb)

            # 6. Composite Pair Risk Calculation
            # Risk = 0.30 * approach + 0.35 * direction + 0.20 * overlap + 0.15 * pose
            raw_risk = (
                (0.30 * p.approach_score) +
                (0.35 * p.direction_score) +
                (0.20 * p.overlap_score) +
                (0.15 * p.pose_anomaly_score)
            )

            # FALSE POSITIVE PROTECTION SUPPRESSION RULES
            if p.direction_score == 0.0: # Parallel walking together
                raw_risk = min(0.15, raw_risk)
            if p.approach_velocity > 2.0: # Separating people
                raw_risk = min(0.10, raw_risk)

            p.risk_score = round(raw_risk, 3)

            # Update Pair State
            if p.risk_score >= 0.65:
                p.interaction_state = InteractionState.HIGH_RISK_INTERACTION
                pose_trigger_needed = True
                explain_reasons.append(f"Pair #{p.track_id_a}-#{p.track_id_b}: High risk ({p.risk_score}) - rapid approach & head-on trajectory")
            elif p.risk_score >= 0.40:
                p.interaction_state = InteractionState.SUSPICIOUS_INTERACTION
                pose_trigger_needed = True
                explain_reasons.append(f"Pair #{p.track_id_a}-#{p.track_id_b}: Suspicious interaction ({p.risk_score})")
            elif p.approach_score > 0.3:
                p.interaction_state = InteractionState.APPROACHING

            if p.risk_score > max_risk:
                max_risk = p.risk_score
                dominant_state = p.interaction_state

        # Prune stale approach histories
        self.approach_engine.prune_stale_pairs(active_pair_keys)

        # 7. Interaction Graph & Crowd Clustering
        clusters, cluster_risk = self.graph_engine.build_graph_and_clusters(tracks, pairs)

        overall_max_risk = max(max_risk, cluster_risk)

        return InteractionEngineResult(
            active_pairs=pairs,
            clusters=clusters,
            max_pair_risk=overall_max_risk,
            cluster_risk=cluster_risk,
            dominant_state=dominant_state,
            pose_trigger_needed=pose_trigger_needed,
            explainability_reasons=explain_reasons
        )
