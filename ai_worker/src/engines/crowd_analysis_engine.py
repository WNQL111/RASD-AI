import logging
import numpy as np
from memory.object_memory import euclidean_distance

logger = logging.getLogger(__name__)

class CrowdAnalysisEngine:
    """
    Computes local computer vision features for crowd dynamics:
    - Crowd density
    - Average speed
    - Motion direction consistency (alignment)
    - Motion variance
    - Local interaction density (number of close interactions)
    - Flow analysis (overall direction and velocity)
    - Group stability
    """
    def __init__(self):
        self.past_groups = []

    def calculate_density(self, tracked_objects, frame_shape=(480, 640)):
        if not tracked_objects:
            return 0.0
        people = [o for o in tracked_objects if (o.get("class_id") if isinstance(o, dict) else getattr(o, "class_id", -1)) == 0]
        return float(len(people))

    def calculate_motion_coherence(self, memory):
        if not memory or not hasattr(memory, 'objects') or not memory.objects:
            return 1.0
        persons = [obj for obj in memory.objects.values() if getattr(obj, 'class_id', -1) == 0]
        if len(persons) < 2:
            return 1.0
        features = self.analyze(persons)
        return features.get("consistency", 1.0)

    def analyze(self, persons):
        """
        Analyze lists of active persons tracked objects to compute features.
        persons: list of tracked ObjectState objects.
        """
        count = len(persons)
        if count == 0:
            return {
                "density": 0,
                "avg_speed": 0.0,
                "consistency": 1.0,
                "variance": 0.0,
                "interaction_density": 0,
                "flow_x": 0.0,
                "flow_y": 0.0,
                "stability": 1.0
            }

        # 1. Density
        density = count

        # Extract velocities and vectors
        speeds = []
        vectors = []
        centers = []
        
        for p in persons:
            speeds.append(p.velocity)
            if len(p.history) >= 2:
                past_bbox = p.history[-2][1]
                past_c = ((past_bbox[0] + past_bbox[2])/2.0, (past_bbox[1] + past_bbox[3])/2.0)
                curr_c = p.get_center()
                vectors.append((curr_c[0] - past_c[0], curr_c[1] - past_c[1]))
            else:
                vectors.append((0.0, 0.0))
            centers.append(p.get_center())

        # 2. Average Speed
        avg_speed = float(np.mean(speeds))

        # 3. Motion Variance
        variance = float(np.var(speeds)) if len(speeds) > 1 else 0.0

        # 4. Motion Direction Consistency
        consistency = 1.0
        valid_vectors = [v for v in vectors if (v[0]**2 + v[1]**2) > 0.1]
        
        if len(valid_vectors) > 1:
            cosines = []
            for i in range(len(valid_vectors)):
                for j in range(i+1, len(valid_vectors)):
                    v1 = valid_vectors[i]
                    v2 = valid_vectors[j]
                    mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
                    mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
                    dot = v1[0]*v2[0] + v1[1]*v2[1]
                    cosines.append(dot / (mag1 * mag2))
            if cosines:
                consistency = float(np.mean(cosines))

        # 5. Local Interaction Density
        interaction_density = 0
        for i in range(count):
            for j in range(i + 1, count):
                if euclidean_distance(centers[i], centers[j]) < 150.0:
                    interaction_density += 1

        # 6. Flow Analysis (overall average motion direction vector)
        flow_x = 0.0
        flow_y = 0.0
        if valid_vectors:
            flow_x = float(np.mean([v[0] for v in valid_vectors]))
            flow_y = float(np.mean([v[1] for v in valid_vectors]))

        # 7. Group Stability
        stability = 1.0
        if count > 1:
            stability = max(0.0, min(1.0, 1.0 - (variance / 50.0) * (1.0 - max(0.0, consistency))))

        # 8. Flow Coherence Suppression Score (CROWD != VIOLENCE)
        suppression_score = 0.0
        if density >= 5 and consistency >= 0.40:
            suppression_score = round(min(0.45, 0.15 + 0.30 * max(0.0, consistency)), 3)

        return {
            "density": density,
            "avg_speed": round(avg_speed, 2),
            "consistency": round(consistency, 2),
            "variance": round(variance, 2),
            "interaction_density": interaction_density,
            "flow_x": round(flow_x, 2),
            "flow_y": round(flow_y, 2),
            "stability": round(stability, 2),
            "suppression_score": suppression_score
        }
