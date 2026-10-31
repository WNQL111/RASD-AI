import numpy as np
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class ObjectState:
    """Represents the rich tracked state of an object in memory."""
    def __init__(self, track_id: int, class_id: int, bbox: list, frame_idx: int):
        self.track_id = track_id
        self.class_id = class_id
        self.bbox = bbox
        self.history = [(frame_idx, bbox)] # List of tuples: (frame_idx, bbox)
        self.velocity = 0.0
        self.acceleration = 0.0
        self.last_seen_frame = frame_idx
        self.lost_state = False
        self.occluded_state = False
        self.owner = None
        self.owner_confidence = 0.0
        self.last_interaction_frame = None

    def get_center(self):
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0

    def update(self, bbox: list, frame_idx: int):
        prev_frame_idx = self.last_seen_frame
        prev_center = self.get_center()
        self.bbox = bbox
        self.history.append((frame_idx, bbox))
        self.last_seen_frame = frame_idx
        self.lost_state = False
        
        curr_center = self.get_center()
        dx = curr_center[0] - prev_center[0]
        dy = curr_center[1] - prev_center[1]
        
        # Normalize velocity by frame index step (dt protection under sparse sampling)
        df = max(1, frame_idx - prev_frame_idx) if prev_frame_idx is not None else 1
        new_velocity = float(np.sqrt(dx**2 + dy**2)) / float(df)
        
        # Calculate acceleration
        self.acceleration = (new_velocity - self.velocity) / float(df)
        self.velocity = new_velocity

        # Keep history bounded
        if len(self.history) > 150:
            self.history.pop(0)

class ObjectMemory:
    """Manages the lifecycle and state estimation of all tracked objects."""
    def __init__(self):
        self.objects = {} # track_id -> ObjectState

    def update_frame(self, tracked_objects: list, frame_idx: int):
        active_ids = set()
        
        for obj in tracked_objects:
            t_id = obj['track_id']
            c_id = obj['class_id']
            bbox = obj['bbox']
            active_ids.add(t_id)

            if t_id not in self.objects:
                self.objects[t_id] = ObjectState(t_id, c_id, bbox, frame_idx)
            else:
                self.objects[t_id].update(bbox, frame_idx)

        # Mark lost objects
        for t_id, state in self.objects.items():
            if t_id not in active_ids:
                if frame_idx - state.last_seen_frame > 5:
                    state.lost_state = True

        # Garbage collect completely stale tracks (no activity for 150 frames)
        for t_id in list(self.objects.keys()):
            if frame_idx - self.objects[t_id].last_seen_frame > 150:
                del self.objects[t_id]

    def get_state(self, track_id: int) -> ObjectState:
        return self.objects.get(track_id)

def euclidean_distance(p1, p2):
    import numpy as np
    return float(np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2))

def calculate_iou(box1, box2):
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Area of overlap
    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y1_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y2_1, y2_2)
    
    overlap_w = max(0.0, xi2 - xi1)
    overlap_h = max(0.0, yi2 - yi1)
    overlap_area = overlap_w * overlap_h
    
    # Area of boxes
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    
    union_area = area1 + area2 - overlap_area
    if union_area == 0.0:
        return 0.0
    return float(overlap_area / union_area)
