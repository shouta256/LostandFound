from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.items import router as items_router

router = APIRouter(prefix="/api/v1")

router.include_router(items_router)
router.include_router(auth_router)
