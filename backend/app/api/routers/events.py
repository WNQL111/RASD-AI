from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from models.models import Event, User
from schemas.schemas import EventResponse
from services.audit import log_action
from core.security import get_current_user

router = APIRouter(tags=["Events"])

@router.get("/events", response_model=List[EventResponse])
def get_events(
    video_id: Optional[str] = None,
    camera_id: Optional[int] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    safe_limit = min(max(1, limit), 100)
    safe_offset = max(0, offset)

    query = db.query(Event)
    if video_id:
        query = query.filter(Event.video_id == video_id)
    if camera_id:
        query = query.filter(Event.camera_id == camera_id)
    if event_type:
        query = query.filter(Event.type == event_type)
    if severity:
        query = query.filter(Event.severity == severity)
        
    return query.order_by(Event.start_time.desc()).offset(safe_offset).limit(safe_limit).all()

@router.post("/events/{event_id}/feedback")
def submit_operator_feedback(
    event_id: int,
    feedback: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    if feedback not in ["Confirmed", "False Alarm"]:
        raise HTTPException(status_code=400, detail="Invalid feedback. Must be 'Confirmed' or 'False Alarm'")
    db_event.operator_feedback = feedback
    db.commit()
    username = current_user.username if current_user else "system"
    log_action(db, username, "operator_feedback", f"Event ID {event_id} feedback set to {feedback}")
    return {"status": "ok", "message": f"Feedback registered for event {event_id}"}

@router.post("/events/{event_id}/link-case/{case_id}")
def assign_event_to_case(
    event_id: int,
    case_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    from models.models import InvestigationCase
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if case_id == 0:
        db_event.case_id = None
        db.commit()
        return {"status": "ok", "message": f"Event {event_id} unlinked from case"}

    db_case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    db_event.case_id = case_id
    db.commit()
    username = current_user.username if current_user else "system"
    log_action(db, username, "assign_case", f"Assigned Event ID {event_id} to Case {db_case.title}")
    return {"status": "ok", "message": f"Event {event_id} linked to Case {case_id}", "case_title": db_case.title}
