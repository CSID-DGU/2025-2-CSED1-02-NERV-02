from fastapi import APIRouter
from app.core import settings
from app.api.v1.endpoints import debug, users, analyses

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["User Management"])
api_router.include_router(analyses.router, prefix="/analyses", tags=["Content Analysis"])

if settings.DEBUG_MODE:
    api_router.include_router(debug.router, prefix="/debug", tags=["Debug & Testing"])