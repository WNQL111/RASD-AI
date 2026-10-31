import math
import logging
import json
from typing import List, Dict, Tuple
from collections import defaultdict
from buffer import TemporalBuffer

logger = logging.getLogger(__name__)

# --- Mathematical Core (Helper Methods) ---

def get_center(bbox: List[float]) -> Tuple[float, float]:
    """Calculate center (x, y) from bbox [x1, y1, x2, y2]."""
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean Distance between two center points."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def calculate_iou(bbox1: List[float], bbox2: List[float]) -> float:
    """Calculate Intersection over Union (IoU) of two bounding boxes."""
    x_left = max(bbox1[0], bbox2[0])
    y_top = max(bbox1[1], bbox2[1])
    x_right = min(bbox1[2], bbox2[2])
    y_bottom = min(bbox1[3], bbox2[3])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    
    iou = intersection_area / float(area1 + area2 - intersection_area)
    return iou


class EventEngine:
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        # --- Configurable Thresholds ---
        self.VIOLENCE_PROXIMITY_THRESH = 350.0  # pixels
        self.VIOLENCE_VELOCITY_THRESH = 6.0     # pixels per frame change
        self.VIOLENCE_DURATION_THRESH = 2       # consecutive frames of condition
 
        self.THEFT_IOU_THRESH = 0.05
        self.THEFT_PROXIMITY_THRESH = 100.0
        self.THEFT_SEPARATION_THRESH = 200.0
        self.THEFT_FLEE_VELOCITY_THRESH = 25.0

        # Collision thresholds
        self.ACCIDENT_DECEL_THRESH = 10.0       # deceleration pixels/frame change
        self.ACCIDENT_IOU_THRESH = 0.08         # overlap threshold

        # State trackers
        self.violence_state = defaultdict(int) # (id1, id2) -> consecutive_frames
        self.theft_state = {} # bag_id -> {"owner_id": person_id, "last_interaction_frame": int}
        self.collision_cooldown = {} # (id1, id2) -> frame_index

    def calculate_velocity(self, track_id: int, buffer: TemporalBuffer, N: int = 5) -> float:
        """Calculate change in center point distance over N frames."""
        history = buffer.get_track_history(track_id)
        if len(history) < N:
            return 0.0
        
        recent = history[-N:]
        start_center = get_center(recent[0]['bbox'])
        end_center = get_center(recent[-1]['bbox'])
        
        dist = euclidean_distance(start_center, end_center)
        # Average pixel displacement per frame
        return dist / N

    def analyze(self, buffer: TemporalBuffer, video_id: str = "sample_video_id"):
        """Main state machine entrypoint to process the temporal buffer."""
        if len(buffer.buffer) == 0:
            return
            
        current_frame_data = buffer.buffer[-1]
        frame_idx = current_frame_data['frame_index']
        tracks = current_frame_data['tracks']
        
        persons = [t for t in tracks if t['class_id'] == 0]
        cars = [t for t in tracks if t['class_id'] == 2]
        # Classes: 24 (backpack), 26 (handbag), 28 (suitcase)
        bags = [t for t in tracks if t['class_id'] in [24, 26, 28]]
        
        self.detect_violence(persons, buffer, frame_idx, video_id)
        self.detect_theft(persons, bags, buffer, frame_idx, video_id)
        self.detect_collision(cars, buffer, frame_idx, video_id)
        self.detect_fire_placeholder(frame_idx, video_id)

    def detect_violence(self, persons: List[Dict], buffer: TemporalBuffer, frame_idx: int, video_id: str):
        """
        Violence Detection Logic (Self-Adaptive Geometric Calibration):
        - Dynamically computes proximity & velocity thresholds relative to the height of persons.
        - Enables seamless performance on street CCTV, shops, malls, and close-up phone cameras.
        """
        for i in range(len(persons)):
            for j in range(i + 1, len(persons)):
                p1 = persons[i]
                p2 = persons[j]
                
                c1 = get_center(p1['bbox'])
                c2 = get_center(p2['bbox'])
                
                dist = euclidean_distance(c1, c2)
                pair = tuple(sorted([p1['track_id'], p2['track_id']]))
                
                # --- Adaptive Calibration ---
                h1 = p1['bbox'][3] - p1['bbox'][1]
                h2 = p2['bbox'][3] - p2['bbox'][1]
                avg_height = (h1 + h2) / 2.0
                
                # Proximity limit (1.5x height, bounded between 100px and 450px)
                adaptive_prox = max(100.0, min(450.0, avg_height * 1.5))
                # Velocity limit (8% of height per frame, bounded between 5px/f and 30px/f)
                adaptive_vel = max(5.0, min(30.0, avg_height * 0.08))
                
                # Condition 1: Proximity
                if dist < adaptive_prox:
                    # Condition 2: Velocity
                    v1 = self.calculate_velocity(p1['track_id'], buffer)
                    v2 = self.calculate_velocity(p2['track_id'], buffer)
                    
                    if v1 > adaptive_vel or v2 > adaptive_vel:
                        self.violence_state[pair] += 1
                        
                        # Condition 3: Duration
                        if self.violence_state[pair] >= self.VIOLENCE_DURATION_THRESH:
                            event = {
                                "video_id": video_id,
                                "type": "violence",
                                "confidence": 0.88,
                                "involved_tracks": list(pair),
                                "frame_index": frame_idx
                            }
                            logger.info(f"🚨 EVENT DETECTED (VIOLENCE): {event} (Adaptive prox={adaptive_prox:.1f}, vel={adaptive_vel:.1f})")
                            if self.redis_client:
                                self.redis_client.publish("asis_events_channel", json.dumps(event))
                            
                            # Reset to avoid continuous spamming for the same interaction
                            self.violence_state[pair] = 0
                        continue
                
                # If conditions fail, reset the duration counter
                self.violence_state[pair] = 0

    def detect_theft(self, persons: List[Dict], bags: List[Dict], buffer: TemporalBuffer, frame_idx: int, video_id: str):
        """
        Theft Detection Logic (Self-Adaptive Geometric Calibration):
        - Scales owner proximity, bag separation, and flee speed thresholds relative to the owner's box height.
        """
        # --- Evaluate State A (Interaction) ---
        for bag in bags:
            bag_id = bag['track_id']
            bag_center = get_center(bag['bbox'])
            
            closest_person_id = None
            min_dist = float('inf')
            
            for person in persons:
                p_center = get_center(person['bbox'])
                p_height = person['bbox'][3] - person['bbox'][1]
                
                # Adaptive proximity threshold (60% of person height)
                adaptive_prox = max(50.0, min(200.0, p_height * 0.6))
                
                dist = euclidean_distance(bag_center, p_center)
                iou = calculate_iou(bag['bbox'], person['bbox'])
                
                if dist < adaptive_prox or iou > self.THEFT_IOU_THRESH:
                    if dist < min_dist:
                        min_dist = dist
                        closest_person_id = person['track_id']
                        
            if closest_person_id is not None:
                # Update interaction state
                self.theft_state[bag_id] = {
                    "owner_id": closest_person_id,
                    "last_interaction_frame": frame_idx
                }
                
        # --- Evaluate State B & C (Separation & Fleeing) ---
        active_bag_ids = {b['track_id'] for b in bags}
        
        for bag_id, state in list(self.theft_state.items()):
            owner_id = state["owner_id"]
            is_separated = False
            
            # State B: Disappearance
            if bag_id not in active_bag_ids:
                is_separated = True
            else:
                # State B: Abrupt distance increase
                current_bag = next((b for b in bags if b['track_id'] == bag_id), None)
                current_owner = next((p for p in persons if p['track_id'] == owner_id), None)
                
                if current_bag and current_owner:
                    dist = euclidean_distance(get_center(current_bag['bbox']), get_center(current_owner['bbox']))
                    o_height = current_owner['bbox'][3] - current_owner['bbox'][1]
                    
                    # Adaptive separation threshold (1.2x owner height)
                    adaptive_sep = max(100.0, min(350.0, o_height * 1.2))
                    
                    if dist > adaptive_sep:
                        is_separated = True
                        
            if is_separated:
                # State C: Fleeing
                current_owner = next((p for p in persons if p['track_id'] == owner_id), None)
                if current_owner:
                    o_height = current_owner['bbox'][3] - current_owner['bbox'][1]
                    # Adaptive fleeing velocity limit (12% of height per frame)
                    adaptive_flee_vel = max(8.0, min(40.0, o_height * 0.12))
                    
                    owner_velocity = self.calculate_velocity(owner_id, buffer, N=5)
                    if owner_velocity > adaptive_flee_vel:
                        event = {
                            "video_id": video_id,
                            "type": "theft",
                            "confidence": 0.92,
                            "involved_tracks": [owner_id],
                            "frame_index": frame_idx
                        }
                        logger.info(f"🚨 EVENT DETECTED (THEFT): {event} (Adaptive sep={adaptive_sep:.1f}, flee={adaptive_flee_vel:.1f})")
                        if self.redis_client:
                            self.redis_client.publish("asis_events_channel", json.dumps(event))
                        
                        # Remove from tracking to prevent duplicate alerts
                        del self.theft_state[bag_id]

    def detect_collision(self, cars: List[Dict], buffer: TemporalBuffer, frame_idx: int, video_id: str):
        """
        Collision Detection Logic (Self-Adaptive Geometric Calibration):
        - Scales overlap proximity and velocity relative to the average size of car bounding boxes.
        """
        for i in range(len(cars)):
            for j in range(i + 1, len(cars)):
                c1 = cars[i]
                c2 = cars[j]
                
                id1, id2 = c1['track_id'], c2['track_id']
                pair = tuple(sorted([id1, id2]))
                
                # Check proximity of centers
                center1 = get_center(c1['bbox'])
                center2 = get_center(c2['bbox'])
                dist = euclidean_distance(center1, center2)
                iou = calculate_iou(c1['bbox'], c2['bbox'])
                
                # --- Adaptive Calibration for Vehicles ---
                w1, h1 = c1['bbox'][2] - c1['bbox'][0], c1['bbox'][3] - c1['bbox'][1]
                w2, h2 = c2['bbox'][2] - c2['bbox'][0], c2['bbox'][3] - c2['bbox'][1]
                avg_car_size = (w1 + h1 + w2 + h2) / 4.0
                
                # Adaptive proximity threshold (1.2x car size, bounded between 40px and 250px)
                adaptive_collision_dist = max(40.0, min(250.0, avg_car_size * 1.2))
                # Adaptive velocity threshold (5% of car size per frame, bounded between 0.5px/f and 10px/f)
                adaptive_collision_vel = max(0.5, min(10.0, avg_car_size * 0.05))
                
                # If they are overlapping or very close
                if iou > 0.03 or dist < adaptive_collision_dist:
                    # Check cooldown
                    if pair in self.collision_cooldown and frame_idx - self.collision_cooldown[pair] < 150:
                        continue
                        
                    # Let's check history to see if one was moving
                    hist1 = buffer.get_track_history(id1)
                    hist2 = buffer.get_track_history(id2)
                    
                    v1 = self.calculate_velocity(id1, buffer, N=min(len(hist1), 3)) if len(hist1) > 1 else 0.0
                    v2 = self.calculate_velocity(id2, buffer, N=min(len(hist2), 3)) if len(hist2) > 1 else 0.0
                    
                    # If at least one car was moving or they have solid overlap
                    if v1 > adaptive_collision_vel or v2 > adaptive_collision_vel or iou > 0.04:
                        event = {
                            "video_id": video_id,
                            "type": "accident",
                            "confidence": 0.94,
                            "involved_tracks": list(pair),
                            "frame_index": frame_idx
                        }
                        logger.info(f"🚨 EVENT DETECTED (COLLISION): {event} (Adaptive dist={adaptive_collision_dist:.1f}, vel={adaptive_collision_vel:.1f})")
                        self.collision_cooldown[pair] = frame_idx
                        if self.redis_client:
                            self.redis_client.publish("asis_events_channel", json.dumps(event))

    def detect_fire_placeholder(self, frame_idx: int, video_id: str):
        """
        Roadmap Stub for Fire/Smoke Detection:
        TODO: Integrate a lightweight binary classification model or semantic segmentation model (e.g. YOLOv8-seg trained on fire/smoke).
        When integrated, this method will run classification on the frame and publish a "fire" event if confidence > threshold.
        """
        pass

    def clear_old_states(self, current_frame_idx: int):
        """Clean up old state trackers to prevent memory leaks in infinite loops."""
        if len(self.violence_state) > 1000:
            self.violence_state.clear()
        
        keys_to_del = [bag_id for bag_id, val in self.theft_state.items() 
                       if current_frame_idx - val.get("last_interaction_frame", 0) > 500]
        for k in keys_to_del:
            self.theft_state.pop(k, None)
            
        cooldown_keys_to_del = [pair for pair, f_idx in self.collision_cooldown.items()
                                if current_frame_idx - f_idx > 300]
        for k in cooldown_keys_to_del:
            self.collision_cooldown.pop(k, None)
