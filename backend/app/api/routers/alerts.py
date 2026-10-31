from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import json
import logging

from db.database import get_db
from models.models import Alert, Event, User, Snapshot, VideoClip, Notification, Track, Video
from schemas.schemas import AlertResponse
from services.audit import log_action
from services.broadcaster import broadcaster
from core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Alerts"])

@router.get("/alerts/stream")
async def stream_alerts(
    request: Request,
    last_event_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Server-Sent Events (SSE) streaming endpoint for real-time security alerts.
    Supports Last-Event-ID header for client reconnection and event resync replay.
    """
    header_last_id = request.headers.get("Last-Event-ID") or last_event_id
    queue = await broadcaster.subscribe()

    async def event_generator():
        try:
            # Send initial retry parameter to EventSource (3000ms reconnect)
            yield "retry: 3000\n\n"

            # Resync missing events if reconnecting with Last-Event-ID
            if header_last_id:
                missed = await broadcaster.get_events_since(header_last_id)
                for item in missed:
                    ev_type = item.get("type", "alert")
                    ev_id = item.get("event_id") or item.get("id")
                    payload = json.dumps(item)
                    yield f"id: {ev_id}\nevent: {ev_type}\ndata: {payload}\n\n"

            while True:
                if await request.is_disconnected():
                    break

                try:
                    raw_json = await asyncio.wait_for(queue.get(), timeout=15.0)
                    try:
                        parsed = json.loads(raw_json)
                        ev_type = parsed.get("type", "alert")
                        ev_id = parsed.get("event_id") or parsed.get("id") or ""
                        source_type = parsed.get("source_type", "LIVE_CAMERA")
                        
                        id_str = f"id: {ev_id}\n" if ev_id else ""
                        yield f"{id_str}event: {ev_type}\ndata: {raw_json}\n\n"
                        
                        # Emit source-scoped and unified events for all security alerts
                        is_threat_event = ev_type not in ["progress_update", "status_update", "analysis_complete", "analysis_failed", "heartbeat"]
                        if is_threat_event:
                            yield f"{id_str}event: live_alert\ndata: {raw_json}\n\n"
                            yield f"{id_str}event: alert\ndata: {raw_json}\n\n"
                            if source_type == "UPLOADED_VIDEO":
                                yield f"{id_str}event: video_job_event\ndata: {raw_json}\n\n"
                    except Exception:
                        yield f"event: alert\ndata: {raw_json}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat comment to keep HTTP connection alive
                    yield ": heartbeat\n\n"
        except (asyncio.CancelledError, Exception) as e:
            logger.info(f"SSE Alert stream client disconnected: {e}")
        finally:
            await broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/alerts", response_model=List[AlertResponse])
def get_alerts(
    source_type: Optional[str] = None,
    video_id: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    safe_limit = min(max(1, limit), 100)
    safe_offset = max(0, offset)

    query = db.query(Alert).join(Event)
    if source_type:
        query = query.filter(Event.source_type == source_type)
    if video_id:
        query = query.filter(Event.video_id == video_id)
    if acknowledged is not None:
        query = query.filter(Alert.acknowledged == acknowledged)
        
    return query.order_by(Alert.id.desc()).offset(safe_offset).limit(safe_limit).all()

@router.delete("/alerts")
def clear_alerts(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    if current_user and current_user.role != "administrator":
        raise HTTPException(status_code=403, detail="Only administrators can clear database records")
        
    try:
        db.query(Alert).delete()
        db.query(Snapshot).delete()
        db.query(VideoClip).delete()
        db.query(Notification).delete()
        db.query(Track).delete()
        db.query(Event).delete()
        db.query(Video).delete()
        
        db.commit()
        username = current_user.username if current_user else "system"
        log_action(db, username, "clear_alerts", "Wiped all alerts, events, and videos from the database")
        return {"status": "ok", "message": "All database records cleared successfully"}
    except Exception as e:
        db.rollback()
        print(f"Error wiping database records: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/alerts/{alert_id}")
def delete_alert(
    alert_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    try:
        db_alert.acknowledged = True
        db_alert.status = "acknowledged"
        if db_alert.event:
            db_alert.event.status = "acknowledged"
        db.commit()
        username = current_user.username if current_user else "system"
        log_action(db, username, "acknowledge_alert", f"Acknowledged alert ID: {alert_id}")
        return {"status": "ok", "message": f"Alert {alert_id} acknowledged successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/alerts/{alert_id}/played-sound")
def mark_alert_sound_played(alert_id: int, db: Session = Depends(get_db)):
    db_alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db_alert.played_sound = True
    db.commit()
    return {"status": "ok"}
