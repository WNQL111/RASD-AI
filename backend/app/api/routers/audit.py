from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from models.models import AuditLog
from schemas.schemas import AuditLogResponse

router = APIRouter(tags=["Audit Logs"])

@router.get("/audit", response_model=List[AuditLogResponse])
def get_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    safe_limit = min(max(1, limit), 200)
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(safe_limit).all()
