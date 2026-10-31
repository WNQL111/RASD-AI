from fastapi import APIRouter

from api.routers.auth import router as auth_router
from api.routers.videos import router as videos_router
from api.routers.events import router as events_router
from api.routers.alerts import router as alerts_router
from api.routers.cameras import router as cameras_router
from api.routers.rules import router as rules_router
from api.routers.health import router as health_router
from api.routers.cases import router as cases_router
from api.routers.audit import router as audit_router

router = APIRouter()

# Aggregate all modular domain routers preserving 100% API contract
router.include_router(auth_router)
router.include_router(videos_router)
router.include_router(events_router)
router.include_router(alerts_router)
router.include_router(cameras_router)
router.include_router(rules_router)
router.include_router(health_router)
router.include_router(cases_router)
router.include_router(audit_router)
