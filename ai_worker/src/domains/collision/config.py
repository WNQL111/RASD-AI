class CollisionConfig:
    # Vehicle class IDs (COCO: bicycle=1, car=2, motorcycle=3, bus=5, truck=7)
    VEHICLE_CLASS_IDS = {1, 2, 3, 5, 7}
    PEDESTRIAN_CLASS_IDS = {0}

    # Physical contact & spatial proximity limits (pixels)
    VEHICLE_VEHICLE_PROXIMITY_THRESH = 110.0
    VEHICLE_PEDESTRIAN_PROXIMITY_THRESH = 90.0
    IOU_OVERLAP_THRESH = 0.003
    GROUND_DISTANCE_THRESH = 100.0

    # Motion & Impact Dynamics Thresholds
    RAPID_APPROACH_RATE_THRESH = 1.5    # Approach speed (px/frame convergence)
    MIN_PRE_IMPACT_SPEED = 1.8          # Minimum pre-impact speed (px/frame)
    DECELERATION_SPIKE_THRESH = 1.5     # Deceleration spike (px/frame^2)
    NORM_DECEL_SPIKE_THRESH = 0.05      # Deceleration relative to box height
    HEADING_DEVIATION_THRESH_DEG = 40.0 # Abrupt heading angle change post-impact
    PARALLEL_COSINE_SIMILARITY = 0.88   # Filter for parallel lane traffic
    HEADON_COSINE_SIMILARITY = -0.40    # Head-on collision threshold

    # Temporal & Persistence Thresholds
    COLLISION_MIN_PERSISTENCE = 3       # Sustained frames before confirmation
    POST_IMPACT_VERIFY_FRAMES = 15      # Frames to monitor aftermath
    HYSTERESIS_DECAY_FRAMES = 10        # Negative frames to reset candidate
    COOLDOWN_SECONDS = 30.0             # Deduplication cooldown per incident
    MEMORY_TTL_SECONDS = 30.0           # State TTL eviction timeout

    # Confidence Thresholds
    MIN_CANDIDATE_CONFIDENCE = 0.25
    CONFIRMATION_THRESHOLD = 0.48
    HIGH_SEVERITY_THRESHOLD = 0.70
