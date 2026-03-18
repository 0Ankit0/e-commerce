from fastapi import APIRouter

from .v1 import router as v1_router

commerce_router = APIRouter()
commerce_router.include_router(v1_router)
