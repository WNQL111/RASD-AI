import json
import logging
from db.database import SessionLocal
from models.models import Video, Event, Alert, Snapshot, VideoClip

logger = logging.getLogger(__name__)

async def listen_to_redis(redis_client):
    if not redis_client:
        logger.warning("Redis client is not configured; redis listener idle.")
        return

    import asyncio
    while True:
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("asis_events_channel")
            logger.info("Subscribed to Redis channel: asis_events_channel (Local 3D Spatio-Temporal Engine)")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        logger.info(f"Received event from Redis: {event_data}")
                        
                        db = SessionLocal()
                        try:
                            if event_data.get("type") == "progress_update":
                                try:
                                    from services.broadcaster import broadcaster
                                    await broadcaster.broadcast(event_data)
                                except Exception as b_err:
                                    logger.error(f"Error broadcasting progress_update: {b_err}")

                            elif event_data.get("type") in ["status_update", "analysis_complete"]:
                                video_id = event_data.get("video_id")
                                status = event_data.get("status", "completed")
                                video = db.query(Video).filter(Video.id == video_id).first()
                                if video:
                                    video.status = status
                                    db.commit()
                                    logger.info(f"Updated Video {video_id} status to {status}")
                                try:
                                    from services.broadcaster import broadcaster
                                    await broadcaster.broadcast(event_data)
                                except Exception as b_err:
                                    logger.error(f"Error broadcasting completion event: {b_err}")

                            elif event_data.get("type") == "analysis_failed":
                                video_id = event_data.get("video_id")
                                video = db.query(Video).filter(Video.id == video_id).first()
                                if video:
                                    video.status = "error"
                                    db.commit()
                                try:
                                    from services.broadcaster import broadcaster
                                    await broadcaster.broadcast(event_data)
                                except Exception as b_err:
                                    logger.error(f"Error broadcasting failure event: {b_err}")
                                    
                            else:
                                raw_type = str(event_data.get("type", "")).lower()
                                # Ignore non-threat telemetry and control messages
                                if raw_type in [
                                    "progress_update", "progress", "status_update",
                                    "analysis_complete", "analysis_failed", "video_analysis_started",
                                    "video_analysis_cancelled", "heartbeat", "telemetry", ""
                                ]:
                                    try:
                                        from services.broadcaster import broadcaster
                                        await broadcaster.broadcast(event_data)
                                    except Exception:
                                        pass
                                    continue

                                # Save standard security event (Strictly Violence & Collision domains)
                                video_id_raw = str(event_data.get("video_id") or event_data.get("source_id") or "")
                                is_live_cam = video_id_raw.startswith("cam_")
                                source_type = event_data.get("source_type") or ("LIVE_CAMERA" if is_live_cam else "UPLOADED_VIDEO")
                                
                                video_id = None if is_live_cam else video_id_raw
                                job_id = event_data.get("job_id") or (None if is_live_cam else video_id_raw)
                                camera_id = event_data.get("camera_id")
                                if is_live_cam and not camera_id:
                                    try:
                                        camera_id = int(video_id_raw.replace("cam_", ""))
                                    except Exception:
                                        pass

                                event_type = event_data.get("type")
                                conf = float(event_data.get("confidence", 0.90))
                                
                                # Determine escalation & risk based on 3D Spatio-Temporal and multi-evidence
                                escalation = event_data.get("escalation_stage", "Confirmed" if conf >= 0.70 else "Likely")
                                severity = event_data.get("severity", "critical" if conf >= 0.85 else "high")
                                risk_score = float(event_data.get("risk_score", conf * 100.0))
                                risk_rating = event_data.get("risk_rating", "CRITICAL" if conf >= 0.85 else "HIGH")

                                explainability_dict = {
                                    **(event_data.get("explainability") or {}),
                                    "verification_status": "LOCAL_3D_VERIFIED",
                                    "timestamp_sec": event_data.get("timestamp_sec", (event_data.get("explainability") or {}).get("timestamp_sec", 0.0)),
                                    "formatted_offset": event_data.get("formatted_offset", (event_data.get("explainability") or {}).get("formatted_offset", "00:00")),
                                    "exact_time_str": event_data.get("exact_time_str", (event_data.get("explainability") or {}).get("exact_time_str", ""))
                                }
                                
                                new_event = Event(
                                    source_type=source_type,
                                    source_id=video_id_raw,
                                    job_id=job_id,
                                    camera_id=camera_id,
                                    video_id=video_id,
                                    trace_id=event_data.get("trace_id"),
                                    reason_codes=event_data.get("reason_codes", []),
                                    type=event_type,
                                    confidence=conf,
                                    involved_track_ids=event_data.get("involved_tracks", event_data.get("involved_track_ids", [])),
                                    severity=severity,
                                    status="unread",
                                    escalation_stage=escalation,
                                    risk_score=risk_score,
                                    risk_rating=risk_rating,
                                    explainability=explainability_dict
                                )
                                db.add(new_event)
                                db.commit()
                                db.refresh(new_event)
                                
                                # Save snapshot
                                snapshot_path = event_data.get("snapshot_path")
                                if snapshot_path:
                                    new_snapshot = Snapshot(
                                        event_id=new_event.id,
                                        image_path=snapshot_path
                                    )
                                    db.add(new_snapshot)
                                    db.commit()
                                    logger.info(f"Associated Snapshot {snapshot_path} with Event {new_event.id}")
                                
                                # Save video clip
                                clip_path = event_data.get("clip_path")
                                if clip_path:
                                    new_clip = VideoClip(
                                        event_id=new_event.id,
                                        clip_path=clip_path,
                                        duration=event_data.get("clip_duration", 15.0)
                                    )
                                    db.add(new_clip)
                                    db.commit()
                                    logger.info(f"Associated VideoClip {clip_path} with Event {new_event.id}")
                                    
                                new_alert = Alert(
                                    event_id=new_event.id,
                                    severity=new_event.severity,
                                    status="unread",
                                    acknowledged=False,
                                    seen=False,
                                    played_sound=False
                                )
                                db.add(new_alert)
                                db.commit()
                                logger.info(f"Saved Local 3D-Verified Event {new_event.id} and Alert ID {new_alert.id} to Database.")

                                # Broadcast confirmed alert to SSE subscribers
                                try:
                                    from services.broadcaster import broadcaster
                                    alert_payload = {
                                        "type": "alert",
                                        "id": new_alert.id,
                                        "event_id": new_event.id,
                                        "source_type": new_event.source_type,
                                        "source_id": new_event.source_id,
                                        "video_id": new_event.video_id,
                                        "severity": new_alert.severity,
                                        "status": new_alert.status,
                                        "acknowledged": new_alert.acknowledged,
                                        "seen": new_alert.seen,
                                        "played_sound": new_alert.played_sound,
                                        "created_at": new_alert.created_at.isoformat() if new_alert.created_at else None,
                                        "event": {
                                            "id": new_event.id,
                                            "video_id": new_event.video_id,
                                            "camera_id": new_event.camera_id,
                                            "type": new_event.type,
                                            "confidence": new_event.confidence,
                                            "severity": new_event.severity,
                                            "escalation_stage": new_event.escalation_stage,
                                            "risk_score": new_event.risk_score,
                                            "risk_rating": new_event.risk_rating,
                                            "explainability": new_event.explainability,
                                            "snapshots": [{"image_path": snapshot_path}] if snapshot_path else [],
                                            "clips": [{"clip_path": clip_path}] if clip_path else []
                                        }
                                    }
                                    await broadcaster.broadcast(alert_payload)
                                    logger.info(f"SSE Broadcaster: Broadcasted Alert ID {new_alert.id} to subscribers.")
                                except Exception as b_err:
                                    logger.error(f"SSE Broadcaster error: {b_err}")

                        except Exception as e:
                            logger.error(f"DB Error while saving event: {e}")
                            db.rollback()
                        finally:
                            db.close()

                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")

        except asyncio.CancelledError:
            logger.info("Redis listener cancelled.")
            break
        except Exception as e:
            logger.warning(f"Redis listener connection error (will retry in 5s): {e}")
            await asyncio.sleep(5)
