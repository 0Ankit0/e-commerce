from fastapi import APIRouter

from .v1 import router as v1_router

catalog_router = APIRouter()
catalog_router.include_router(v1_router)
