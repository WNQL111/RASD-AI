import sys
import os
import json
import argparse

# Add backend and ai_worker directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))

from app.db.database import SessionLocal
from app.models.models import Video, Event, Alert, Snapshot, VideoClip

def inspect_job(job_id: str):
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == job_id).first()
        if not video:
            print(f"[-] Analysis Job ID '{job_id}' not found in Database.")
            return

        print("==========================================================")
        print(f"ASIS-V2 EVIDENCE TRACE & DECISION INSPECTOR")
        print("==========================================================")
        print(f"Job ID         : {video.id}")
        print(f"Filename       : {video.filename}")
        print(f"Video Status   : {video.status}")
        print(f"Created At     : {video.created_at}")

        events = db.query(Event).filter(Event.job_id == job_id).order_by(Event.start_time.asc()).all()
        if not events:
            # Fallback to video_id query
            events = db.query(Event).filter(Event.video_id == job_id).order_by(Event.start_time.asc()).all()

        print(f"\n[+] Total Events Detected for Job: {len(events)}")
        
        for idx, ev in enumerate(events, 1):
            print(f"\n--- Event #{idx} ---")
            print(f"Event ID       : {ev.id}")
            print(f"Trace ID       : {ev.trace_id}")
            print(f"Type           : {ev.type}")
            print(f"Source Type    : {ev.source_type}")
            print(f"Source ID      : {ev.source_id}")
            print(f"Confidence     : {ev.confidence * 100:.1f}%")
            print(f"Severity       : {ev.severity}")
            print(f"Stage          : {ev.escalation_stage}")
            print(f"Risk Score     : {ev.risk_score:.1f}")
            print(f"Risk Rating    : {ev.risk_rating}")
            print(f"Tracks Involved: {ev.involved_track_ids}")
            print(f"Reason Codes   : {ev.reason_codes}")

            if ev.explainability:
                exp = ev.explainability
                print(f"Explainability Tree:")
                tree = exp.get("explainability_tree", {})
                for step in tree.get("steps", []):
                    status_str = "[PASS]" if step.get("status") else "[SKIP]"
                    print(f"  {status_str} {step.get('name')}: score={step.get('score', 0):.2f} (weight={step.get('weight', 0):.2f})")
                print(f"Matched Zones : {exp.get('matched_zones', [])}")

    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASIS-V2 Video Decision Inspector")
    parser.add_argument("--job-id", type=str, required=True, help="Job ID / Video ID to inspect")
    args = parser.parse_args()
    inspect_job(args.job_id)
