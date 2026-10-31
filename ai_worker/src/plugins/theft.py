import logging
from plugins.base import BasePlugin
from memory.object_memory import ObjectMemory, euclidean_distance, calculate_iou
from detectors.registry import PortableObjectRegistry

logger = logging.getLogger(__name__)

class TheftPlugin(BasePlugin):
    """
    Universal Theft Detection Plugin.
    Implements a full 11-step theft lifecycle state machine supporting all portable assets:
    IDLE -> PLACED -> OWNER_ASSIGNED -> OWNER_LEAVES -> GRACE_PERIOD -> SUSPECT_APPROACHES -> TOUCHES -> CARRIES -> MOVING_AWAY -> RUNS -> CONFIRMED
    """
    def __init__(self, rule_engine):
        super().__init__(rule_engine)
        # Maps object_track_id -> State Dict
        self.theft_states = {}

    @property
    def name(self) -> str:
        return "theft"

    def analyze(self, memory: ObjectMemory, frame_idx: int, video_id: str) -> list:
        events = []
        
        # Load rule parameters
        theft_prox = self.rule_engine.get_float("theft_proximity_thresh", 100.0)
        theft_sep = self.rule_engine.get_float("theft_separation_thresh", 200.0)
        flee_vel_base = self.rule_engine.get_float("theft_flee_velocity_thresh", 25.0)
        
        # Get active persons and portable objects
        persons = {state.track_id: state for state in memory.objects.values() if state.class_id == 0 and not state.lost_state}
        portables = {state.track_id: state for state in memory.objects.values() if state.class_id in PortableObjectRegistry.get_registered_classes()}

        # Clean up stale states for deleted objects
        for obj_id in list(self.theft_states.keys()):
            if obj_id not in portables:
                # If a carrying suspect exists, they might have exited the frame (theft confirmed)
                state = self.theft_states[obj_id]
                if state["state"] in ["CARRIES", "RUNS"]:
                    state["state"] = "CONFIRMED"
                else:
                    del self.theft_states[obj_id]

        for obj_id, port in portables.items():
            # Initial state
            if obj_id not in self.theft_states:
                self.theft_states[obj_id] = {
                    "state": "IDLE",
                    "owner_id": port.owner,
                    "suspect_id": None,
                    "grace_frames": 0,
                    "placed_pos": port.get_center(),
                    "frame_history": []
                }
            
            state = self.theft_states[obj_id]
            state["frame_history"].append(frame_idx)
            
            current_state = state["state"]
            owner_id = port.owner
            
            # --- 11-step Theft State Machine Transitions ---
            
            if current_state == "IDLE":
                if port.owner is not None:
                    state["state"] = "OBJECT_PLACED"
                    state["owner_id"] = port.owner
            
            elif current_state == "OBJECT_PLACED":
                if port.owner_confidence > 0.5:
                    state["state"] = "OWNER_ASSIGNED"
                    
            elif current_state == "OWNER_ASSIGNED":
                # Check if owner leaves (distance increases beyond separation threshold)
                if owner_id in persons:
                    owner = persons[owner_id]
                    dist = euclidean_distance(port.get_center(), owner.get_center())
                    
                    # Scale thresholds based on owner height
                    h_owner = owner.bbox[3] - owner.bbox[1]
                    adaptive_sep = max(100.0, min(theft_sep * 1.5, h_owner * 1.2))
                    
                    if dist > adaptive_sep:
                        state["state"] = "OWNER_LEAVES"
                elif port.owner is not None:
                    # Owner disappeared from view
                    state["state"] = "OWNER_LEAVES"

            elif current_state == "OWNER_LEAVES":
                state["state"] = "GRACE_PERIOD"
                state["grace_frames"] = 0

            elif current_state == "GRACE_PERIOD":
                state["grace_frames"] += 1
                
                # Check if owner returns
                owner_returned = False
                if owner_id in persons:
                    owner = persons[owner_id]
                    dist = euclidean_distance(port.get_center(), owner.get_center())
                    h_owner = owner.bbox[3] - owner.bbox[1]
                    adaptive_prox = max(50.0, min(theft_prox * 1.5, h_owner * 0.60))
                    if dist < adaptive_prox:
                        owner_returned = True
                        
                if owner_returned:
                    state["state"] = "OWNER_ASSIGNED"
                    state["grace_frames"] = 0
                elif state["grace_frames"] > 30: # 30 frames grace period (approx 1 second)
                    # Grace period expired, object is alone and vulnerable. Check if suspect approaches
                    suspect = self.find_approaching_stranger(port, persons, owner_id, theft_prox)
                    if suspect:
                        state["state"] = "SUSPECT_APPROACHES"
                        state["suspect_id"] = suspect.track_id

            elif current_state == "SUSPECT_APPROACHES":
                # If owner returns, abort
                if self.is_owner_near(port, persons, owner_id, theft_prox):
                    state["state"] = "OWNER_ASSIGNED"
                    state["suspect_id"] = None
                    continue
                    
                suspect_id = state["suspect_id"]
                if suspect_id in persons:
                    suspect = persons[suspect_id]
                    iou = calculate_iou(port.bbox, suspect.bbox)
                    dist = euclidean_distance(port.get_center(), suspect.get_center())
                    
                    h_suspect = suspect.bbox[3] - suspect.bbox[1]
                    adaptive_prox = max(50.0, min(theft_prox * 1.5, h_suspect * 0.60))
                    
                    if iou > 0.05 or dist < adaptive_prox:
                        state["state"] = "TOUCHES"

            elif current_state == "TOUCHES":
                suspect_id = state["suspect_id"]
                if suspect_id in persons:
                    suspect = persons[suspect_id]
                    # If suspect moves with the object (object center follows suspect center)
                    port_center = port.get_center()
                    susp_center = suspect.get_center()
                    dist = euclidean_distance(port_center, susp_center)
                    
                    if dist < 120.0 and port.velocity > 1.0:
                        state["state"] = "CARRIES"

            elif current_state == "CARRIES":
                suspect_id = state["suspect_id"]
                if suspect_id in persons:
                    suspect = persons[suspect_id]
                    # Check if carrying suspect moves away from the placement zone
                    dist_from_start = euclidean_distance(port.get_center(), state["placed_pos"])
                    h_suspect = suspect.bbox[3] - suspect.bbox[1]
                    adaptive_sep = max(100.0, min(theft_sep * 1.5, h_suspect * 1.2))

                    if dist_from_start > adaptive_sep:
                        state["state"] = "MOVING_AWAY"

            elif current_state == "MOVING_AWAY":
                suspect_id = state["suspect_id"]
                if suspect_id in persons:
                    suspect = persons[suspect_id]
                    h_suspect = suspect.bbox[3] - suspect.bbox[1]
                    adaptive_flee = max(8.0, min(flee_vel_base, h_suspect * 0.12))
                    
                    if suspect.velocity > adaptive_flee:
                        state["state"] = "RUNS"
                    else:
                        # Even if they walk away slowly, if they exceed separation limit far enough, confirm theft
                        dist_from_start = euclidean_distance(port.get_center(), state["placed_pos"])
                        if dist_from_start > adaptive_sep * 2:
                            state["state"] = "CONFIRMED"

            elif current_state == "RUNS":
                state["state"] = "CONFIRMED"

            if state["state"] == "CONFIRMED":
                item_name = PortableObjectRegistry.get_item_name(port.class_id)
                suspect_label = f"Person #{state['suspect_id']}" if state['suspect_id'] else "unknown suspect"
                
                events.append({
                    "video_id": video_id,
                    "type": f"theft_{item_name}",
                    "confidence": 0.95,
                    "severity": "critical",
                    "involved_tracks": [state["suspect_id"]] if state["suspect_id"] else [],
                    "frame_index": frame_idx,
                    "details": f"Theft of {item_name} confirmed by suspect {suspect_label}. Owner ID: {state['owner_id']}"
                })
                # Reset state machine to RESOLVED to prevent duplicate alerts
                state["state"] = "RESOLVED"

        return events

    def find_approaching_stranger(self, port, persons, owner_id, threshold):
        for person in persons.values():
            if person.track_id == owner_id:
                continue
            dist = euclidean_distance(port.get_center(), person.get_center())
            h_person = person.bbox[3] - person.bbox[1]
            adaptive_prox = max(80.0, min(threshold * 2.0, h_person * 1.0))
            if dist < adaptive_prox:
                return person
        return None

    def is_owner_near(self, port, persons, owner_id, threshold):
        if owner_id in persons:
            owner = persons[owner_id]
            dist = euclidean_distance(port.get_center(), owner.get_center())
            h_owner = owner.bbox[3] - owner.bbox[1]
            adaptive_prox = max(50.0, min(threshold * 1.5, h_owner * 0.60))
            return dist < adaptive_prox
        return False
