from contextlib import asynccontextmanager
from app.core import settings
from app.core.logging import setup_logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.services.filtering.kiwi_engine import KiwiEngine
from app.services.filtering.first_pass_filter import FirstPassFilter
from app.services.filtering.second_pass_filter import SecondPassFilter
from app.services.filtering.risk_scorer import RiskScorer
from app.services.filtering.policy_manager import PolicyManager

from app.services.filtering.system_dict_loader import load_system_dict
from app.api.v1.api import api_router
from app.db import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    system_dict, system_user_words = load_system_dict()
    app.state.system_dict = system_dict

    # Kiwi 싱글톤 (FirstPassFilter + 트렌딩 키워드 추출 공유)
    kiwi_engine = KiwiEngine(system_words=system_user_words)
    app.state.kiwi_engine = kiwi_engine

    app.state.first_pass_filter = FirstPassFilter(kiwi_engine)
    app.state.second_pass_filter = SecondPassFilter()
    app.state.risk_scorer = RiskScorer()
    app.state.policy_manager = PolicyManager()

    yield

setup_logging()

app = FastAPI(
    title="YouTube Comment Filtering System API",
    description="YouTube Comment Filtering System API",
    version="1.0.2",
    openapi_version="3.0.2",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "YouTube Comment Filtering System API is running. Visit /docs for API documentation."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
