from fastapi import APIRouter

from .v1 import router as v1_router

logistics_router = APIRouter()
logistics_router.include_router(v1_router)
