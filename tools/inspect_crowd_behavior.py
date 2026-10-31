import sys
import os
import cv2
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src")))

from detectors.yolo_detector import YoloDetector
from tracker.byte_tracker import ByteTracker
from core.pipeline import Pipeline

def inspect_crowd(video_path: str = "WWD(MP4).mp4"):
    if not os.path.exists(video_path):
        print(f"File {video_path} not found.")
        return

    cap = cv2.VideoCapture(video_path)
    detector = YoloDetector(model_dir="models", model_name="yolov8n.pt")
    tracker = ByteTracker(detector)
    pipeline = Pipeline(detector=detector)

    frame_idx = 0
    print(f"=== Inspecting Crowd Behavioral Trace: {video_path} ===")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        evs = pipeline.process_frame(frame, frame_idx, video_id=os.path.basename(video_path), tracker=tracker)
        if frame_idx % 30 == 0 or evs:
            state = getattr(pipeline.scene_profiler.scene_state_machine, 'current_state', 'N/A')
            p_cnt = len([o for o in pipeline.memory.objects.values() if not o.lost_state and o.class_id == 0]) if hasattr(pipeline, 'memory') else 0
            print(f"Frame [{frame_idx:04d}] | State: {state:<12} | People: {p_cnt:<3} | Events Emitted: {len(evs) if evs else 0}")
            if evs:
                for e in evs:
                    print(f"  --> EVENT: {getattr(e, 'type', 'N/A')} | Severity: {getattr(e, 'severity', 'N/A')} | Risk: {getattr(e, 'risk_score', 0.0)}")

        frame_idx += 1

    cap.release()
    print("=== Inspection Complete ===")

if __name__ == "__main__":
    v_path = sys.argv[1] if len(sys.argv) > 1 else "WWD(MP4).mp4"
    inspect_crowd(v_path)
