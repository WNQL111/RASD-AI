from sqlalchemy.orm import Session
from models.models import AuditLog

def log_action(db: Session, username: str, action: str, details: str = None):
    try:
        new_log = AuditLog(
            username=username if username else "system",
            action=action,
            details=details
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error writing audit log: {e}")
