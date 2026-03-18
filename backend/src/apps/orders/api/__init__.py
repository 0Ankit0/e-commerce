from fastapi import APIRouter

from .v1 import router as v1_router

orders_router = APIRouter()
orders_router.include_router(v1_router)
