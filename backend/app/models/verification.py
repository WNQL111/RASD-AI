from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from datetime import datetime
from db.database import Base

class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(String, index=True, nullable=False)
    provider = Column(String, index=True)
    request_time = Column(DateTime, default=datetime.utcnow)
    response_time = Column(DateTime, nullable=True)
    status = Column(String, default="PENDING")  # PENDING, VERIFIED, DISAGREED, MANUAL_REVIEW, FALSE_ALARM
    agree = Column(Boolean, nullable=True)
    confidence = Column(Float, nullable=True)
    reason_ar = Column(String, nullable=True)
    reason_en = Column(String, nullable=True)
    raw_response = Column(JSON, nullable=True)
    cost = Column(Float, default=0.0)
    cached = Column(Boolean, default=False)
    latency = Column(Float, default=0.0)
