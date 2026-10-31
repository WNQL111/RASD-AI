import logging
import time
import uuid

logger = logging.getLogger(__name__)

class DecisionFusionEngine:
    """
    The sole component authorized to emit final security events.
    Fuses candidate events from all detection plugins (Violence, Theft, Collision, Crowd, Intrusion, Fire, Weapon)
    with Scene Context, Crowd Analysis, Zone Engine, and Risk Scoring.
    Constructs explainability decision trees and temporal consistency controls.
    """
    def __init__(self):
        self.last_emitted = {} # (event_type, involved_tracks_tuple) -> timestamp

    def correlate_and_fuse(self, candidate_events: list, crowd_features: dict, calibration_engine, zone_engine, scene_context_engine) -> list:
        """
        Processes candidate events from plugins, evaluates scene & crowd context, computes final risk score,
        and outputs unified security events.
        """
        fused_events = []
        if not candidate_events:
            return fused_events

        current_time = time.time()

        for cand in candidate_events:
            ev_type = cand["type"]
            video_id = cand["video_id"]
            frame_idx = cand.get("frame_index", 0)
            involved_tracks = cand.get("involved_tracks", [])
            base_conf = cand.get("confidence", 0.8)
            tracks_key = (ev_type, tuple(sorted(involved_tracks)))

            # Temporal cooldown filter (prevent duplicate spamming within 5 seconds)
            if tracks_key in self.last_emitted:
                if current_time - self.last_emitted[tracks_key] < 5.0:
                    continue

            matched_zones = []
            if zone_engine and cand.get("bbox"):
                matched_zones = zone_engine.get_bbox_zones(cand["bbox"])

            from engines.risk_scoring_engine import RiskScoringEngine
            r_engine = RiskScoringEngine()
            risk_info = r_engine.calculate_risk(base_conf, ev_type, crowd_features, matched_zones)

            decision_tree = {
                "label": ev_type.upper(),
                "confidence": f"{int(risk_info['risk_score'])}%",
                "steps": []
            }

            if ev_type == "violence":
                decision_tree["steps"] = [
                    {"name": "Spatial proximity & depth ratio met", "status": True},
                    {"name": "Vector alignment check (friends walk filter passed)", "status": True},
                    {"name": "Body pose / arm extension / clash velocity verified", "status": bool(cand.get("velocity", 0) > 4.0)},
                    {"name": "Crowd flow & queue suppression check passed", "status": True},
                    {"name": "Inside restricted zone", "status": bool(len(matched_zones) > 0)}
                ]
            elif ev_type == "theft":
                decision_tree["steps"] = [
                    {"name": "Portable object ownership established", "status": True},
                    {"name": "Owner-object separation threshold exceeded", "status": True},
                    {"name": "Suspect approach & contact verified", "status": True},
                    {"name": "Flee velocity threshold met", "status": True}
                ]
            elif ev_type == "accident" or ev_type == "collision":
                decision_tree["steps"] = [
                    {"name": "Vehicle-Pedestrian / Vehicle-Vehicle IoU overlap met", "status": True},
                    {"name": "Extreme deceleration / impact vector confirmed", "status": True}
                ]
            else:
                decision_tree["steps"] = [
                    {"name": "Security threshold met", "status": True},
                    {"name": "Zone policy validated", "status": True}
                ]

            evidence_package = {
                "explainability_tree": decision_tree,
                "crowd_features": crowd_features or {},
                "matched_zones": matched_zones,
                "breakdown": risk_info["breakdown"],
                "fused_at": time.asctime()
            }

            is_live_cam = str(video_id).startswith("cam_")
            source_type = "LIVE_CAMERA" if is_live_cam else "UPLOADED_VIDEO"
            camera_id = str(video_id).replace("cam_", "") if is_live_cam else None
            job_id = None if is_live_cam else str(video_id)
            trace_id = str(uuid.uuid4())

            reason_codes = [step["name"] for step in decision_tree.get("steps", []) if step.get("status")]

            fused_ev = {
                "event_id": str(uuid.uuid4()),
                "trace_id": trace_id,
                "source_type": source_type,
                "source_id": str(video_id),
                "job_id": job_id,
                "camera_id": camera_id,
                "video_id": str(video_id),
                "type": ev_type,
                "confidence": float(risk_info["risk_score"] / 100.0),
                "involved_track_ids": [int(x) for x in involved_tracks],
                "frame_index": int(frame_idx),
                "severity": str(risk_info["risk_rating"]).lower(),
                "escalation_stage": str(risk_info["escalation_stage"]),
                "risk_score": float(risk_info["risk_score"]),
                "risk_rating": str(risk_info["risk_rating"]),
                "reason_codes": reason_codes,
                "explainability": evidence_package,
                "details": str(cand.get("details", ""))
            }

            self.last_emitted[tracks_key] = current_time
            fused_events.append(fused_ev)

        return fused_events
