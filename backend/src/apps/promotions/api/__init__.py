from fastapi import APIRouter

from .v1 import router as v1_router

promotions_router = APIRouter()
promotions_router.include_router(v1_router)
