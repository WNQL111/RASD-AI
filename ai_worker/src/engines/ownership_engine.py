import logging
from memory.object_memory import ObjectMemory, ObjectState
from detectors.registry import PortableObjectRegistry

logger = logging.getLogger(__name__)

def calculate_iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    if x2 < x1 or y2 < y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    return intersection / union if union > 0 else 0.0

def euclidean_distance(p1, p2):
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5

class OwnershipEngine:
    """
    Manages dynamic, confidence-based ownership of portable assets.
    Owner association increases gradually during close contact (preventing instant swaps during occlusions).
    """
    def __init__(self):
        # Maps portable_id -> owner_id
        # We can dynamically retrieve values from ObjectMemory states
        pass

    def update_ownership(self, memory: ObjectMemory, frame_idx: int, proximity_thresh: float = 120.0):
        persons = [state for state in memory.objects.values() if state.class_id == 0 and not state.lost_state]
        portables = [state for state in memory.objects.values() if state.class_id in PortableObjectRegistry.get_registered_classes()]

        for port in portables:
            # Find closest person
            closest_person = None
            min_dist = float('inf')
            best_iou = 0.0
            
            p_center = port.get_center()

            for person in persons:
                dist = euclidean_distance(p_center, person.get_center())
                iou = calculate_iou(port.bbox, person.bbox)

                # Use person height to dynamically scale proximity check
                h_person = person.bbox[3] - person.bbox[1]
                adaptive_thresh = max(60.0, min(proximity_thresh * 1.5, h_person * 0.75))

                if dist < adaptive_thresh or iou > 0.05:
                    if dist < min_dist:
                        min_dist = dist
                        closest_person = person
                        best_iou = max(best_iou, iou)

            if closest_person is not None:
                # If there's already an owner
                if port.owner is not None:
                    if port.owner == closest_person.track_id:
                        # Owner is still interacting, raise confidence gradually
                        port.owner_confidence = min(1.0, port.owner_confidence + 0.15)
                        port.last_interaction_frame = frame_idx
                    else:
                        # Another person is interacting. Decrease current owner confidence first
                        port.owner_confidence = max(0.0, port.owner_confidence - 0.08)
                        if port.owner_confidence <= 0.0:
                            # Ownership transfers only when previous owner confidence reaches 0
                            logger.info(f"Ownership of {port.track_id} ({PortableObjectRegistry.get_item_name(port.class_id)}) transferred from {port.owner} to {closest_person.track_id}")
                            port.owner = closest_person.track_id
                            port.owner_confidence = 0.15
                            port.last_interaction_frame = frame_idx
                else:
                    # New owner assigned
                    port.owner = closest_person.track_id
                    port.owner_confidence = 0.15
                    port.last_interaction_frame = frame_idx
            else:
                # No person interacting. Decays ownership confidence slowly
                if port.owner is not None:
                    port.owner_confidence = max(0.0, port.owner_confidence - 0.01)
                    # We keep the owner association even if confidence decays, until a new person claims it
