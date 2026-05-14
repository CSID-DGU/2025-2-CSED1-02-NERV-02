"""FastAPI 필터 서비스 — nerv-filter SDK 의 얇은 HTTP 래퍼.

엔드포인트:
- GET  /health           헬스 체크
- POST /analyze          단일 텍스트 분석
- POST /analyze/batch    배치 분석
- GET  /info             SDK / 사전 정보

Spring 앱이 내부 호출 용도. 외부 노출 안 됨.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from nerv_filter import NervFilter, SecurityLevel


# ─────────────────────────────────────────────
# Lifespan — 앱 시작 시 NervFilter 1회만 초기화
# ─────────────────────────────────────────────
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["filter"] = NervFilter(security_level=SecurityLevel.MEDIUM)
    yield
    _state.clear()


def get_filter() -> NervFilter:
    flt = _state.get("filter")
    if flt is None:
        raise HTTPException(status_code=503, detail="Filter not initialized")
    return flt


app = FastAPI(
    title="nerv-overlay filter service",
    description="Internal filter service wrapping nerv-filter SDK.",
    version="0.1.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────
# 요청/응답 스키마
# ─────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="분석할 텍스트")
    security_level: SecurityLevel = Field(SecurityLevel.MEDIUM, description="정책 강도")


class BatchRequest(BaseModel):
    texts: list[str]
    security_level: SecurityLevel = SecurityLevel.MEDIUM


class DetectedWordOut(BaseModel):
    word: str
    type: str


class FlagsOut(BaseModel):
    has_blacklist: bool
    has_general: bool
    has_trigger: bool


class AnalyzeResponse(BaseModel):
    original_text: str
    masked_text: str
    action: str
    score: float
    detected_words: list[DetectedWordOut]
    flags: FlagsOut


# ─────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────
def _to_response(result) -> AnalyzeResponse:
    return AnalyzeResponse(
        original_text=result.original_text,
        masked_text=result.masked_text,
        action=result.action.value,
        score=result.score,
        detected_words=[
            DetectedWordOut(word=d.word, type=d.word_type.value)
            for d in result.detected_words
        ],
        flags=FlagsOut(
            has_blacklist=result.flags.has_blacklist,
            has_general=result.flags.has_general,
            has_trigger=result.flags.has_trigger,
        ),
    )


# ─────────────────────────────────────────────
# 엔드포인트
# ─────────────────────────────────────────────
@app.get("/health")
async def health(flt: Annotated[NervFilter, Depends(get_filter)]):
    return {
        "status": "ok",
        "dictionary_size": flt.get_dictionary_size(),
    }


@app.get("/info")
async def info(flt: Annotated[NervFilter, Depends(get_filter)]):
    from nerv_filter import __version__

    return {
        "sdk_version": __version__,
        "dictionary_size": flt.get_dictionary_size(),
        "security_level": flt.security_level.value,
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    req: AnalyzeRequest,
    flt: Annotated[NervFilter, Depends(get_filter)],
):
    """단일 텍스트 분석.

    보안 수준은 호출마다 달라질 수 있어 인스턴스의 setter 로 변경한다.
    Kiwi 재로드 비용이 매우 커서 NervFilter 인스턴스를 새로 만들지 않는다.
    """
    if req.security_level != flt.security_level:
        flt.security_level = req.security_level

    result = flt.analyze(req.text)
    return _to_response(result)


@app.post("/analyze/batch", response_model=list[AnalyzeResponse])
async def analyze_batch(
    req: BatchRequest,
    flt: Annotated[NervFilter, Depends(get_filter)],
):
    if req.security_level != flt.security_level:
        flt.security_level = req.security_level

    results = flt.analyze_batch(req.texts)
    return [_to_response(r) for r in results]
