from fastapi import APIRouter

from .v1 import router as v1_router

recommendations_router = APIRouter()
recommendations_router.include_router(v1_router)
