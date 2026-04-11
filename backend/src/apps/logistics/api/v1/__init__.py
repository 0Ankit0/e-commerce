from fastapi import APIRouter

from .planning import router as planning_router
from .routes import router as operations_router

router = APIRouter()
router.include_router(operations_router)
router.include_router(planning_router)

__all__ = ["router"]
