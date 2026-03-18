from fastapi import APIRouter

from .v1 import router as v1_router

vendors_router = APIRouter()
vendors_router.include_router(v1_router)
