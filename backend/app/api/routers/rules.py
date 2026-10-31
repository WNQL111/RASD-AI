from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import json
import redis

from db.database import get_db
from models.models import Rule, RuleVersion, User
from schemas.schemas import RuleResponse, RuleCreate, RuleVersionResponse
from services.audit import log_action
from core.security import get_current_user

router = APIRouter(tags=["Rules"])

def get_redis():
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    return redis.from_url(redis_url, socket_connect_timeout=0.1, socket_timeout=0.1, decode_responses=True)

@router.get("/rules", response_model=List[RuleResponse])
def get_rules(db: Session = Depends(get_db)):
    rules = db.query(Rule).all()
    if not rules:
        defaults = {
            "violence_proximity_thresh": "350.0",
            "violence_velocity_thresh": "6.0",
            "violence_duration_thresh": "2",
            "violence_pose_energy_thresh": "15.0",
            "violence_confidence_thresh": "0.75",
            "collision_decel_thresh": "10.0",
            "collision_iou_thresh": "0.08",
            "collision_confidence_thresh": "0.70",
            "spatiotemporal_3d_enabled": "true",
            "spatiotemporal_window_frames": "16",
            "pre_event_roll": "5.0",
            "post_event_roll": "10.0"
        }
        for key, val in defaults.items():
            new_rule = Rule(key=key, value=val)
            db.add(new_rule)
        db.commit()
        rules = db.query(Rule).all()
    return rules

@router.post("/rules", response_model=RuleResponse)
def set_rule(
    rule_in: RuleCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    db_rule = db.query(Rule).filter(Rule.key == rule_in.key).first()
    if db_rule:
        db_rule.value = rule_in.value
        db_rule.camera_id = rule_in.camera_id
        db_rule.updated_at = datetime.utcnow()
    else:
        db_rule = Rule(key=rule_in.key, value=rule_in.value, camera_id=rule_in.camera_id)
        db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    username = current_user.username if current_user else "system"
    log_action(db, username, "set_rule", f"Updated rule threshold: {db_rule.key} = {db_rule.value}")

    try:
        r = get_redis()
        r.publish("camera_control_channel", json.dumps({
            "command": "config_update"
        }))
    except Exception as e:
        print(f"Error publishing config_update command to Redis: {e}")

    return db_rule

@router.get("/rules/versions/{rule_key}", response_model=List[RuleVersionResponse])
def get_rule_versions(rule_key: str, db: Session = Depends(get_db)):
    return db.query(RuleVersion).filter(RuleVersion.rule_key == rule_key).order_by(RuleVersion.version_number.desc()).all()
