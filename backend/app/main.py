# -*- coding: utf-8 -*-
"""
RASD AI (رَصْد AI) - Main Application Gateway & REST API Entrypoint
===================================================================
Role & Responsibilities:
  - Initializes FastAPI application instance and CORS middleware.
  - Manages asynchronous application lifespan, background tasks, and Redis listener.
  - Executes non-destructive self-healing database schema migrations on startup.
  - Mounts API routers under `/api` and static forensic video vaults under `/videos`.
  - Serves root identity metadata and system health telemetry endpoints.
"""
import sys
import os

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

_AI_WORKER_SRC = os.path.abspath(os.path.join(_CURRENT_DIR, "..", "..", "ai_worker", "src"))
if os.path.exists(_AI_WORKER_SRC) and _AI_WORKER_SRC not in sys.path:
    sys.path.insert(0, _AI_WORKER_SRC)

from fastapi import FastAPI
from contextlib import asynccontextmanager
import redis.asyncio as redis
import logging
import asyncio
from fastapi.middleware.cors import CORSMiddleware

from db.database import engine, Base
from api.endpoints import router as api_router
from services.redis_listener import listen_to_redis

from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
from db.database import engine, Base
from sqlalchemy import text
from models.verification import VerificationRequest

# Create tables
Base.metadata.create_all(bind=engine)

# Run simple ALTER migrations to support live DB updates
try:
    is_sqlite = engine.name == "sqlite"
    with engine.connect() as conn:
        if not is_sqlite:
            statements = [
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS camera_id INTEGER REFERENCES cameras(id);",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS severity VARCHAR DEFAULT 'high';",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'unread';",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS source_type VARCHAR DEFAULT 'LIVE_CAMERA';",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS source_id VARCHAR;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS job_id VARCHAR REFERENCES videos(id);",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS trace_id VARCHAR;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS reason_codes JSON;",
                "ALTER TABLE tracks ADD COLUMN IF NOT EXISTS camera_id INTEGER REFERENCES cameras(id);",
                "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS scene_type VARCHAR DEFAULT 'Mall';",
                "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS sensitivity VARCHAR DEFAULT 'Medium';",
                "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS replay_length INTEGER DEFAULT 15;",
                "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS rules_enabled JSON;",
                "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS calibration JSON;",
                "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS model_profile VARCHAR DEFAULT 'yolov8n.pt';",
                "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS zones JSON;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS escalation_stage VARCHAR DEFAULT 'Suspicious';",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS risk_score FLOAT DEFAULT 0.0;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS risk_rating VARCHAR DEFAULT 'LOW';",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS explainability JSON;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS operator_feedback VARCHAR;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS case_id INTEGER;",
                "ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS vram_usage FLOAT;",
                "ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS dropped_frames INTEGER DEFAULT 0;",
                "CREATE INDEX IF NOT EXISTS idx_events_camera_id ON events(camera_id);",
                "CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged);",
                "CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);"
            ]
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception as stmt_err:
                    conn.rollback()
        logging.getLogger(__name__).info("Database migrations and performance indexes executed successfully.")
except Exception as e:
    logging.getLogger(__name__).error(f"Migration error: {e}")

# Seed default camera and rules if empty
try:
    from db.database import SessionLocal
    from models.models import Camera, Rule, Video
    db = SessionLocal()
    if db.query(Camera).count() == 0:
        default_cam = Camera(
            name="ALHIY",
            stream_url="http://192.168.8.108:8080/video",
            stream_type="mjpeg",
            status="online",
            is_analysis_running=False
        )
        db.add(default_cam)
        db.commit()
        logging.getLogger(__name__).info("Database seeded with default camera ALHIY.")

    # Automatically resolve stale processing videos from previous restarts
    stale_videos = db.query(Video).filter(Video.status == 'processing').all()
    if stale_videos:
        for sv in stale_videos:
            sv.status = 'completed'
        db.commit()
        logging.getLogger(__name__).info("Updated stale processing videos to completed on startup.")
        
    # Seed rules table if rules count is small or empty
    if db.query(Rule).filter(Rule.key == "violence_proximity_thresh").count() == 0:
        default_rules = [
            Rule(key="violence_proximity_thresh", value="350"),
            Rule(key="violence_velocity_thresh", value="6"),
            Rule(key="violence_duration_thresh", value="2"),
            Rule(key="violence_cooldown_sec", value="30"),
            Rule(key="theft_proximity_thresh", value="100"),
            Rule(key="theft_separation_thresh", value="200"),
            Rule(key="theft_flee_velocity_thresh", value="25"),
            Rule(key="ai_provider", value="Disabled"),
            Rule(key="api_key", value=""),
            Rule(key="external_verification_min_thresh", value="40.0"),
            Rule(key="external_verification_max_thresh", value="75.0"),
            Rule(key="active_ai_model", value="yolov8n.pt")
        ]
        db.add_all(default_rules)
        db.commit()
        logging.getLogger(__name__).info("Database seeded with default rules thresholds.")
    db.close()
except Exception as e:
    logging.getLogger(__name__).error(f"Seeding error: {e}")

redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        logger.info(f"Initialized Redis client for {redis_url}")
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {e}")
        redis_client = None
    
    # Start Redis Listener in background
    listener_task = asyncio.create_task(listen_to_redis(redis_client)) if redis_client else None
    
    yield
    
    if listener_task:
        listener_task.cancel()
    if redis_client:
        try:
            await redis_client.close()
        except Exception:
            pass
    logger.info("Application shutdown completed.")

app = FastAPI(
    title="RASD AI API",
    description="RASD AI (رَصْد AI) - AI-Powered Local Video Surveillance, Incident Detection and Forensic Analysis Platform",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the specific frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from services.storage import get_storage_dir

app.include_router(api_router, prefix="/api")
storage_videos_dir = get_storage_dir()
os.makedirs(storage_videos_dir, exist_ok=True)
app.mount("/videos", StaticFiles(directory=storage_videos_dir), name="videos")

@app.get("/")
async def root():
    return {"name": "RASD AI", "name_ar": "رَصْد AI", "tagline": "AI-Powered Local Video Surveillance, Incident Detection and Forensic Analysis Platform", "version": "2.0.0", "status": "online"}

@app.get("/health")
async def health_check():
    try:
        ping = await redis_client.ping()
        redis_status = "ok" if ping else "failed"
    except Exception as e:
        redis_status = f"error: {str(e)}"
        
    return {
        "status": "ok",
        "redis": redis_status
    }
