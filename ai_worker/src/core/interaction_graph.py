import logging
from typing import List, Dict, Set, Tuple
from core.scene_types import TrackContext
from core.interaction_types import InteractionPair, InteractionCluster, InteractionState

logger = logging.getLogger(__name__)

class InteractionGraph:
    """
    Interaction Graph & Clustering Engine for ASIS-V2.
    Builds spatial-temporal interaction graph (Nodes=Tracks, Edges=Pairs).
    Groups connected components into InteractionClusters during crowd mode.
    """
    def build_graph_and_clusters(
        self,
        tracks: List[TrackContext],
        active_pairs: List[InteractionPair]
    ) -> Tuple[List[InteractionCluster], float]:
        """
        Builds clusters from connected pairs and returns (clusters, max_cluster_risk).
        """
        if not active_pairs:
            return [], 0.0

        # Build Adjacency List
        adj: Dict[int, Set[int]] = {}
        pair_lookup: Dict[Tuple[int, int], InteractionPair] = {}

        for p in active_pairs:
            key = (min(p.track_id_a, p.track_id_b), max(p.track_id_a, p.track_id_b))
            pair_lookup[key] = p

            if p.track_id_a not in adj:
                adj[p.track_id_a] = set()
            if p.track_id_b not in adj:
                adj[p.track_id_b] = set()

            adj[p.track_id_a].add(p.track_id_b)
            adj[p.track_id_b].add(p.track_id_a)

        # Connected Components (BFS/DFS)
        visited = set()
        clusters: List[InteractionCluster] = []
        cluster_id_counter = 1
        max_cluster_risk = 0.0

        for tid in list(adj.keys()):
            if tid in visited:
                continue

            component_tids = []
            queue = [tid]
            visited.add(tid)

            while queue:
                curr = queue.pop(0)
                component_tids.append(curr)
                for neighbor in adj.get(curr, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            if len(component_tids) >= 2:
                # Find all pairs within this cluster component
                cluster_pairs = []
                cluster_motion = 0.0
                max_p_risk = 0.0

                for i in range(len(component_tids)):
                    for j in range(i + 1, len(component_tids)):
                        ckey = (min(component_tids[i], component_tids[j]), max(component_tids[i], component_tids[j]))
                        if ckey in pair_lookup:
                            cp = pair_lookup[ckey]
                            cluster_pairs.append(cp)
                            cluster_motion += cp.relative_velocity
                            if cp.risk_score > max_p_risk:
                                max_p_risk = cp.risk_score

                cluster_density = round(len(cluster_pairs) / float(len(component_tids)), 2)
                cluster_conflict = round(max_p_risk * min(1.0, len(cluster_pairs) * 0.3), 3)

                if cluster_conflict > max_cluster_risk:
                    max_cluster_risk = cluster_conflict

                cluster = InteractionCluster(
                    cluster_id=cluster_id_counter,
                    track_ids=component_tids,
                    pairs=cluster_pairs,
                    density=cluster_density,
                    motion_energy=round(cluster_motion, 2),
                    conflict_score=cluster_conflict
                )
                clusters.append(cluster)
                cluster_id_counter += 1

        return clusters, max_cluster_risk
