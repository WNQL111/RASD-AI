from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
import redis

from db.database import get_db
from models.models import Camera, User
from schemas.schemas import CameraCreate, CameraResponse
from services.audit import log_action
from core.security import get_current_user

router = APIRouter(tags=["Cameras"])

def get_redis():
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    return redis.from_url(redis_url, socket_connect_timeout=0.1, socket_timeout=0.1, decode_responses=True)

@router.get("/cameras", response_model=List[CameraResponse])
def get_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).all()

def normalize_camera_stream_url(url: str) -> str:
    if not url:
        return ""
    s = str(url).strip()
    if s.isdigit():
        return s
    if not (s.startswith("http://") or s.startswith("https://") or s.startswith("rtsp://")):
        s = "http://" + s
    try:
        from urllib.parse import urlparse
        parsed = urlparse(s)
        path = parsed.path.strip()
        # IP Webcam / Phone streaming apps running on 8080/8081/4747 need /video endpoint
        if (parsed.port in [8080, 8081, 4747] or ":8080" in s) and (not path or path == "/"):
            return f"{s.rstrip('/')}/video"
    except Exception:
        pass
    return s

@router.post("/cameras", response_model=CameraResponse)
def create_camera(
    camera: CameraCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    raw_url = (camera.stream_url or "").strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="يجب تزويد رابط البث أو عنوان الكاميرا")

    # 1. Format and sanitize URL with automatic endpoint resolution
    clean_url = normalize_camera_stream_url(raw_url)
    if clean_url.isdigit():
        detected_type = "webcam"
    elif clean_url.startswith("rtsp://"):
        detected_type = "rtsp"
    else:
        detected_type = camera.stream_type or "mjpeg"

    # 2. Derive intuitive camera name if omitted
    cam_name = (camera.name or "").strip()
    if not cam_name:
        count = db.query(Camera).count() + 1
        if clean_url.isdigit():
            cam_name = f"كاميرا مدمجة #{clean_url}"
        else:
            cam_name = f"كاميرا {count}"

    existing = db.query(Camera).filter(Camera.stream_url == clean_url).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"رابط الكاميرا مسجل مسبقاً باسم '{existing.name}'")

    new_cam = Camera(
        name=cam_name,
        stream_url=clean_url,
        stream_type=detected_type,
        status="online",
        is_analysis_running=True,
        scene_type=camera.scene_type or "Mall",
        sensitivity=camera.sensitivity or "Medium",
        model_profile=camera.model_profile or "yolov8n.pt",
        replay_length=camera.replay_length or 15,
        rules_enabled=camera.rules_enabled or ["violence", "collision"],
        calibration=camera.calibration or {},
        zones=camera.zones or []
    )
    db.add(new_cam)
    db.commit()
    db.refresh(new_cam)

    # 3. Dispatch start command via Redis or Native fallback
    dispatched_redis = False
    try:
        r = get_redis()
        subs = r.publish("camera_control_channel", json.dumps({
            "command": "start",
            "camera_id": new_cam.id,
            "stream_url": new_cam.stream_url,
            "stream_type": new_cam.stream_type
        }))
        if subs > 0:
            dispatched_redis = True
    except Exception:
        pass

    if not dispatched_redis and new_cam.stream_url:
        with active_camera_threads_lock:
            stop_evt = threading.Event()
            th = threading.Thread(
                target=_run_local_camera_analysis,
                args=(new_cam.id, new_cam.stream_url, stop_evt),
                daemon=True
            )
            th.start()
            active_camera_threads[new_cam.id] = {"stop_event": stop_evt, "thread": th}

    username = current_user.username if current_user else "system"
    log_action(db, username, "create_camera", f"Created new camera: {new_cam.name} (URL: {new_cam.stream_url})")
    return new_cam

@router.get("/cameras/{cam_id}", response_model=CameraResponse)
def get_camera(cam_id: int, db: Session = Depends(get_db)):
    db_cam = db.query(Camera).filter(Camera.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return db_cam

@router.put("/cameras/{cam_id}", response_model=CameraResponse)
def update_camera(
    cam_id: int, 
    camera: CameraCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_cam = db.query(Camera).filter(Camera.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    clean_url = camera.stream_url.strip() if camera.stream_url else ""
    db_cam.name = camera.name
    db_cam.stream_url = clean_url
    db_cam.stream_type = camera.stream_type
    db_cam.scene_type = camera.scene_type
    db_cam.sensitivity = camera.sensitivity
    if hasattr(camera, 'model_profile') and camera.model_profile:
        db_cam.model_profile = camera.model_profile
    db_cam.replay_length = camera.replay_length
    db_cam.rules_enabled = camera.rules_enabled
    db_cam.calibration = camera.calibration
    db_cam.zones = camera.zones
    
    db.commit()
    db.refresh(db_cam)
    
    username = current_user.username if current_user else "system"
    log_action(db, username, "update_camera", f"Updated camera ID: {cam_id} profile: {db_cam.name}")
    return db_cam

@router.delete("/cameras/{cam_id}")
def delete_camera(
    cam_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_cam = db.query(Camera).filter(Camera.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    if db_cam.is_analysis_running:
        try:
            r = get_redis()
            r.publish("camera_control_channel", json.dumps({
                "command": "stop",
                "camera_id": cam_id,
                "stream_url": db_cam.stream_url
            }))
        except Exception as e:
            print(f"Error publishing stop command to Redis: {e}")
            
    db.delete(db_cam)
    db.commit()
    
    username = current_user.username if current_user else "system"
    log_action(db, username, "delete_camera", f"Deleted camera ID: {cam_id}")
    return {"status": "ok", "message": f"Camera {cam_id} deleted successfully"}

import threading
import cv2
import numpy as np
from datetime import datetime
from services.broadcaster import broadcaster

# In-Memory Active Camera Analysis Registry
active_camera_threads: dict = {}
active_camera_threads_lock = threading.Lock()

def is_url_reachable(url: str, timeout: float = 0.5) -> bool:
    if not url:
        return False
    if str(url).strip().isdigit():
        return True  # Local device index (e.g. 0 for webcam)
    s = normalize_camera_stream_url(str(url).strip())
    if not (s.startswith("http://") or s.startswith("https://") or s.startswith("rtsp://")):
        return True  # Local video file path
    try:
        from urllib.parse import urlparse
        import socket
        parsed = urlparse(s)
        host = parsed.hostname
        port = parsed.port or (80 if parsed.scheme == "http" else 443 if parsed.scheme == "https" else 554)
        if not host:
            return False
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def make_camera_status_frame(name: str, stream_url: str, message: str = "CONNECTING") -> bytes:
    img = np.full((360, 640, 3), (28, 22, 17), dtype=np.uint8)  # Dark slate background
    cv2.rectangle(img, (8, 8), (632, 352), (55, 45, 35), 2)
    # Camera Title
    cv2.putText(img, f"CAMERA: {name}", (25, 55), cv2.FONT_HERSHEY_DUPLEX, 0.85, (240, 240, 240), 2)
    # Status Indicator
    is_offline = "OFFLINE" in message or "WAITING" in message or "FAILED" in message
    circle_color = (0, 0, 220) if is_offline else (0, 165, 255)
    cv2.circle(img, (32, 115), 7, circle_color, -1)
    cv2.putText(img, f"STATUS: {message}", (50, 122), cv2.FONT_HERSHEY_SIMPLEX, 0.65, circle_color, 2)
    # Stream URL
    display_url = (stream_url[:55] + "...") if len(stream_url) > 55 else stream_url
    cv2.putText(img, f"STREAM URL: {display_url}", (25, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (170, 170, 170), 1)
    # Diagnostics Advice
    cv2.putText(img, "Ensure camera app/stream is active and on the same Wi-Fi network", (25, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (130, 130, 130), 1)
    cv2.putText(img, "Stream will display automatically as soon as frames are received.", (25, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (99, 102, 241), 1)
    # Live Clock
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(img, now_str, (25, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 100, 100), 1)
    
    ret, jpeg = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    return jpeg.tobytes() if ret else b""

def _run_local_camera_analysis(cam_id: int, stream_url: str, stop_event: threading.Event):
    from db.database import SessionLocal
    from models.models import Event, Alert, Snapshot, VideoClip
    import sys
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    ai_src = os.path.join(base_dir, "ai_worker", "src")
    if ai_src not in sys.path:
        sys.path.insert(0, ai_src)

    from core.pipeline import AIPipeline
    from detectors.yolo_detector import YoloDetector
    from tracker.byte_tracker import ByteTracker

    models_dir = os.path.join(base_dir, "models")
    detector = YoloDetector(model_dir=models_dir, model_name="yolov8n.pt")
    pipeline = AIPipeline(detector=detector, fps=15.0)
    tracker = ByteTracker(detector)

    norm_url = normalize_camera_stream_url(stream_url)
    source = int(norm_url) if norm_url.isdigit() else norm_url
    cap = None
    frame_idx = 0

    while not stop_event.is_set():
        if cap is None or not cap.isOpened():
            if not is_url_reachable(norm_url, timeout=0.5):
                for _ in range(15):
                    if stop_event.is_set():
                        break
                    time.sleep(0.2)
                continue
            try:
                cap = cv2.VideoCapture(source)
                if hasattr(cv2, 'CAP_PROP_BUFFERSIZE'):
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                cap = None
            if not cap or not cap.isOpened():
                for _ in range(15):
                    if stop_event.is_set():
                        break
                    time.sleep(0.2)
                continue

        ret, frame = cap.read()
        if not ret or frame is None:
            if cap:
                cap.release()
            cap = None
            time.sleep(0.5)
            continue

        if frame_idx % 2 == 0:  # Efficient 15 FPS analysis
            h, w = frame.shape[:2]
            target_w = min(640, w)
            target_h = int(h * (target_w / w))
            frame_resized = cv2.resize(frame, (target_w, target_h))

            events = pipeline.process_frame(frame_resized, frame_idx, f"cam_{cam_id}", tracker)
            if events:
                db = SessionLocal()
                try:
                    for ev in events:
                        ev_type = ev.get("type", "violence")
                        conf = float(ev.get("confidence", 0.85))
                        new_ev = Event(
                            camera_id=cam_id,
                            source_type="LIVE_CAMERA",
                            source_id=f"cam_{cam_id}",
                            type=ev_type,
                            start_time=datetime.utcnow(),
                            confidence=conf,
                            severity="critical" if conf >= 0.85 else "high",
                            status="unread",
                            escalation_stage="Confirmed",
                            risk_score=float(ev.get("risk_score", conf * 100.0)),
                            risk_rating="CRITICAL" if conf >= 0.85 else "HIGH",
                            involved_track_ids=ev.get("involved_tracks", []),
                            reason_codes=ev.get("reasons", []),
                            explainability=ev.get("explainability", {})
                        )
                        db.add(new_ev)
                        db.commit()
                        db.refresh(new_ev)

                        snap_path = ev.get("snapshot_path")
                        if snap_path:
                            db.add(Snapshot(event_id=new_ev.id, image_path=snap_path))
                            db.commit()

                        new_al = Alert(event_id=new_ev.id, severity=new_ev.severity, status="unread", acknowledged=False)
                        db.add(new_al)
                        db.commit()
                        db.refresh(new_al)

                        broadcaster.broadcast_sync({
                            "type": "alert",
                            "id": new_al.id,
                            "event_id": new_ev.id,
                            "camera_id": cam_id,
                            "source_type": "LIVE_CAMERA",
                            "source_id": f"cam_{cam_id}",
                            "severity": new_al.severity,
                            "status": new_al.status,
                            "created_at": datetime.utcnow().isoformat(),
                            "event": {
                                "id": new_ev.id,
                                "type": new_ev.type,
                                "confidence": new_ev.confidence,
                                "severity": new_ev.severity,
                                "snapshots": [{"image_path": snap_path}] if snap_path else []
                            }
                        })
                except Exception as db_err:
                    print(f"Error persisting camera {cam_id} event: {db_err}")
                finally:
                    db.close()

        frame_idx += 1
        time.sleep(0.02)

    if cap:
        cap.release()

@router.post("/cameras/{cam_id}/start-analysis", response_model=CameraResponse)
def start_analysis(
    cam_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_cam = db.query(Camera).filter(Camera.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    db_cam.is_analysis_running = True
    db.commit()
    db.refresh(db_cam)

    # 1. Dispatch via Redis if available
    dispatched_redis = False
    try:
        r = get_redis()
        subs = r.publish("camera_control_channel", json.dumps({
            "command": "start",
            "camera_id": cam_id,
            "stream_url": db_cam.stream_url,
            "stream_type": db_cam.stream_type
        }))
        if subs > 0:
            dispatched_redis = True
    except Exception:
        pass

    # 2. Local fallback analysis thread (Native Mode)
    if not dispatched_redis and db_cam.stream_url:
        with active_camera_threads_lock:
            if cam_id in active_camera_threads:
                active_camera_threads[cam_id]["stop_event"].set()
                del active_camera_threads[cam_id]

            stop_evt = threading.Event()
            th = threading.Thread(
                target=_run_local_camera_analysis,
                args=(cam_id, db_cam.stream_url, stop_evt),
                daemon=True
            )
            th.start()
            active_camera_threads[cam_id] = {"stop_event": stop_evt, "thread": th}

    username = current_user.username if current_user else "system"
    log_action(db, username, "start_analysis", f"Triggered live analysis on camera: {db_cam.name}")
    return db_cam

@router.post("/cameras/{cam_id}/stop-analysis", response_model=CameraResponse)
def stop_analysis(
    cam_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_cam = db.query(Camera).filter(Camera.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    db_cam.is_analysis_running = False
    db.commit()
    db.refresh(db_cam)

    # Stop local analysis thread if active
    with active_camera_threads_lock:
        if cam_id in active_camera_threads:
            active_camera_threads[cam_id]["stop_event"].set()
            del active_camera_threads[cam_id]

    try:
        r = get_redis()
        r.publish("camera_control_channel", json.dumps({
            "command": "stop",
            "camera_id": cam_id,
            "stream_url": db_cam.stream_url
        }))
    except Exception:
        pass

    username = current_user.username if current_user else "system"
    log_action(db, username, "stop_analysis", f"Stopped live analysis on camera: {db_cam.name}")
    return db_cam

@router.get("/cameras/{cam_id}/video_feed")
def get_camera_video_feed(cam_id: int):
    import time
    from db.database import SessionLocal

    def event_generator():
        db = SessionLocal()
        cam = db.query(Camera).filter(Camera.id == cam_id).first()
        cam_name = cam.name if cam else f"Camera #{cam_id}"
        stream_url = (cam.stream_url.strip() if cam and cam.stream_url else "")
        db.close()

        if not stream_url:
            offline_bytes = make_camera_status_frame(cam_name, "None", "NO STREAM URL CONFIGURED")
            while True:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + offline_bytes + b'\r\n')
                time.sleep(2.0)

        # 1. Check if Redis has frames (if running in Docker with ai_worker)
        r = None
        try:
            r = get_redis()
            r.ping()
        except Exception:
            r = None

        cap = None
        last_connect_try = 0.0

        while True:
            # Check Redis frames
            if r:
                try:
                    frame_bytes = r.get(f"camera:{cam_id}:latest_frame")
                    if frame_bytes:
                        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                        time.sleep(0.04)
                        continue
                except Exception:
                    pass

            # 2. Direct Camera Stream Handling (Native Mode)
            norm_url = normalize_camera_stream_url(stream_url)
            now = time.time()
            if cap is None or not cap.isOpened():
                if now - last_connect_try >= 2.0:
                    last_connect_try = now
                    if is_url_reachable(norm_url, timeout=0.5):
                        try:
                            source = int(norm_url) if norm_url.isdigit() else norm_url
                            cap = cv2.VideoCapture(source)
                            if hasattr(cv2, 'CAP_PROP_BUFFERSIZE'):
                                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        except Exception:
                            cap = None
                    else:
                        cap = None

            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    target_w = min(640, w)
                    target_h = int(h * (target_w / w))
                    frame_resized = cv2.resize(frame, (target_w, target_h))
                    ret_enc, jpeg = cv2.imencode('.jpg', frame_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    if ret_enc:
                        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                        time.sleep(0.033)  # ~30 FPS
                        continue
                else:
                    cap.release()
                    cap = None

            # 3. Stream status diagnostic frame if disconnected/connecting
            status_msg = "STREAM RECONNECTING..." if (cap and not cap.isOpened()) else "CAMERA OFFLINE / WAITING FOR STREAM"
            status_frame = make_camera_status_frame(cam_name, norm_url, status_msg)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + status_frame + b'\r\n')
            time.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="multipart/x-mixed-replace; boundary=frame")
