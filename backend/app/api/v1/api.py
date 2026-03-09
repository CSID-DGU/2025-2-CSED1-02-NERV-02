from fastapi import APIRouter

from app.api.v1.endpoints import modules, system, workflow

api_router = APIRouter()

api_router.include_router(modules.router, prefix="/modules", tags=["Unit Tests (Modules)"])
api_router.include_router(system.router, prefix="/system", tags=["System & Config"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["Integrative Workflow (Full Process)"])