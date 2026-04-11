from fastapi import APIRouter

from .notifications import router as notifications_router
from .notification_preferences import router as preferences_router
from .push_devices import router as push_router
from .quota_admin import router as quota_admin_router

router = APIRouter()
router.include_router(preferences_router)   # static paths must come before /{id}
router.include_router(push_router)
router.include_router(notifications_router)

router.include_router(quota_admin_router)
