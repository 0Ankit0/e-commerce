from fastapi import APIRouter

from .v1 import router as v1_router

messaging_router = APIRouter()
messaging_router.include_router(v1_router)
