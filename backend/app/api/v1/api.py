from fastapi import APIRouter
from app.core import settings
from app.api.v1.endpoints import debug, users, analyses, auth, ai_training

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["User Management"])
api_router.include_router(analyses.router, prefix="/analyses", tags=["Content Analysis"])
api_router.include_router(ai_training.router, prefix="/ai-training", tags=["AI Training"])

if settings.DEBUG_MODE:
    api_router.include_router(debug.router, prefix="/debug", tags=["Debug & Testing"])