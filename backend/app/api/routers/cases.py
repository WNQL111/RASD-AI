from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from models.models import InvestigationCase, Event, User
from schemas.schemas import InvestigationCaseCreate, InvestigationCaseResponse
from services.audit import log_action
from core.security import get_current_user

router = APIRouter(tags=["Cases"])

@router.get("/cases", response_model=List[InvestigationCaseResponse])
def get_cases(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    safe_limit = min(max(1, limit), 100)
    safe_offset = max(0, offset)

    query = db.query(InvestigationCase)
    if status:
        query = query.filter(InvestigationCase.status == status)
        
    return query.order_by(InvestigationCase.created_at.desc()).offset(safe_offset).limit(safe_limit).all()

@router.post("/cases", response_model=InvestigationCaseResponse)
def create_case(
    case_in: InvestigationCaseCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    import re
    new_case = InvestigationCase(
        title=case_in.title,
        description=case_in.description,
        status=case_in.status or "open",
        assigned_operator=case_in.assigned_operator,
        resolution_notes=case_in.resolution_notes
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    # 1. Collect target event IDs to link
    events_to_link = set()
    if case_in.event_id:
        events_to_link.add(case_in.event_id)
    if case_in.event_ids:
        events_to_link.update(case_in.event_ids)

    # 2. Heuristic linking from Title / Description if user mentioned an event ID
    combined_text = f"{case_in.title or ''} {case_in.description or ''}"
    # Match patterns like #12, Event 12, حادث 12
    matches = re.findall(r'(?:#|ID:\s*|Event\s*|حادث\s*)(\d+)', combined_text, re.IGNORECASE)
    for m in matches:
        try:
            cand_id = int(m)
            if db.query(Event).filter(Event.id == cand_id).first():
                events_to_link.add(cand_id)
        except ValueError:
            pass

    # 3. Apply links
    if events_to_link:
        for eid in events_to_link:
            ev = db.query(Event).filter(Event.id == eid).first()
            if ev:
                ev.case_id = new_case.id
        db.commit()
        db.refresh(new_case)

    username = current_user.username if current_user else "system"
    log_action(db, username, "create_case", f"Created investigation case: {new_case.title} (Linked {len(events_to_link)} events)")
    return new_case

@router.get("/cases/{case_id}", response_model=InvestigationCaseResponse)
def get_case(case_id: int, db: Session = Depends(get_db)):
    db_case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case

@router.put("/cases/{case_id}", response_model=InvestigationCaseResponse)
def update_case(
    case_id: int,
    case_in: InvestigationCaseCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    db_case.title = case_in.title
    db_case.description = case_in.description
    db_case.status = case_in.status
    db_case.assigned_operator = case_in.assigned_operator
    db_case.resolution_notes = case_in.resolution_notes
    db.commit()
    db.refresh(db_case)
    username = current_user.username if current_user else "system"
    log_action(db, username, "update_case", f"Updated case: {db_case.title} (Status: {db_case.status})")
    return db_case

@router.delete("/cases/{case_id}")
def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    for ev in db_case.events:
        ev.case_id = None
    db.delete(db_case)
    db.commit()
    username = current_user.username if current_user else "system"
    log_action(db, username, "delete_case", f"Deleted case ID: {case_id}")
    return {"status": "ok", "message": f"Case {case_id} deleted successfully"}

@router.post("/cases/{case_id}/link-event/{event_id}", response_model=InvestigationCaseResponse)
def link_event_to_case(
    case_id: int,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_case or not db_event:
        raise HTTPException(status_code=404, detail="Case or Event not found")
    db_event.case_id = case_id
    db.commit()
    db.refresh(db_case)
    username = current_user.username if current_user else "system"
    log_action(db, username, "link_event", f"Linked Event ID {event_id} to Case {db_case.title}")
    return db_case

@router.post("/cases/{case_id}/events", response_model=InvestigationCaseResponse)
def add_event_to_case_body(
    case_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    ev_id = payload.get("event_id")
    if not ev_id:
        raise HTTPException(status_code=400, detail="event_id is required in body")
    return link_event_to_case(case_id=case_id, event_id=int(ev_id), db=db, current_user=current_user)

@router.post("/cases/{case_id}/unlink-event/{event_id}", response_model=InvestigationCaseResponse)
def unlink_event_from_case(
    case_id: int,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_case or not db_event:
        raise HTTPException(status_code=404, detail="Case or Event not found")
    if db_event.case_id == case_id:
        db_event.case_id = None
        db.commit()
        db.refresh(db_case)
    username = current_user.username if current_user else "system"
    log_action(db, username, "unlink_event", f"Unlinked Event ID {event_id} from Case {db_case.title}")
    return db_case
