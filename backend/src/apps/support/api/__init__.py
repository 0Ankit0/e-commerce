from fastapi import APIRouter

from .v1 import router as v1_router

support_router = APIRouter()
support_router.include_router(v1_router)
