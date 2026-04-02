from contextlib import asynccontextmanager
from app.core import settings
from app.core.logging import setup_logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.services.filtering.first_pass_filter import FirstPassFilter
from app.services.filtering.second_pass_filter import SecondPassFilter
from app.services.filtering.risk_scorer import RiskScorer
from app.services.filtering.policy_manager import PolicyManager
from app.services.filtering.keyword_extractor import KeywordExtractor

from app.repositories.dictionary import load_system_dict
from app.api.v1.api import api_router
from app.db import Base, engine, AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        app.state.system_dict = await load_system_dict(session)

    app.state.first_pass_filter = FirstPassFilter()
    app.state.second_pass_filter = SecondPassFilter()
    app.state.risk_scorer = RiskScorer()
    app.state.policy_manager = PolicyManager()
    app.state.keyword_extractor = KeywordExtractor()

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
