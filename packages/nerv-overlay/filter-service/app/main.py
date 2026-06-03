"""FastAPI 필터 서비스 — nerv-filter SDK 의 얇은 HTTP 래퍼.

엔드포인트:
- GET  /health           헬스 체크
- POST /analyze          단일 텍스트 분석
- POST /analyze/batch    배치 분석
- POST /train-one        2차 모듈 실시간 단일 학습 (활성 시)
- GET  /info             SDK / 사전 정보

Spring 앱이 내부 호출 용도. 외부 노출 안 됨.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from nerv_filter import NervFilter, SecurityLevel


# ─────────────────────────────────────────────
# Lifespan — 앱 시작 시 NervFilter 1회만 초기화
# ─────────────────────────────────────────────
_state: dict = {}

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 2차 필터 — 환경변수 기반. SECOND_PASS_ENABLED=false 면 강제 1차만.
    # 그 외에는 SDK 동봉 attention head + KcBERT 다운로드(첫 호출 시)로 활성화.
    second_pass = None
    try:
        from nerv_filter.second_pass import SecondPassConfig

        sp = SecondPassConfig.from_env()
        if sp.is_enabled:
            second_pass = sp
            logger.info(
                "[filter-service] 2차 필터 설정: models=%s threshold=%s modules_root=%s",
                sp.models, sp.threshold, sp.resolved_modules_root,
            )
        else:
            logger.info("[filter-service] 2차 필터 비활성 (1차만)")
    except Exception as e:
        logger.warning("[filter-service] 2차 설정 로드 실패, 1차만: %s", e)

    _state["filter"] = NervFilter(security_level=SecurityLevel.MEDIUM, second_pass=second_pass)
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
    version="0.2.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────
# 요청/응답 스키마
# ─────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="분석할 텍스트")
    security_level: SecurityLevel = Field(SecurityLevel.MEDIUM, description="정책 강도")
    whitelist: list[str] | None = Field(None, description="요청별 화이트리스트 override")
    blacklist: list[str] | None = Field(None, description="요청별 블랙리스트 override")
    use_ai_filter: bool = Field(True, description="이 호출에 2차(AI) 필터 사용 여부")


class BatchRequest(BaseModel):
    texts: list[str]
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    whitelist: list[str] | None = None
    blacklist: list[str] | None = None
    use_ai_filter: bool = True


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


class TrainOneRequest(BaseModel):
    module_name: str = Field(..., examples=["sexual"])
    text: str = Field(..., min_length=1)
    label: int = Field(..., ge=0, le=1)
    save: bool = Field(default=True)


class TrainOneResponse(BaseModel):
    module: str
    loss: float
    score_after_step: float
    saved: bool


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
    sp = getattr(flt, "_second_pass", None)
    return {
        "status": "ok",
        "dictionary_size": flt.get_dictionary_size(),
        "second_pass_active": bool(sp and sp.is_active),
    }


@app.get("/info")
async def info(flt: Annotated[NervFilter, Depends(get_filter)]):
    from nerv_filter import __version__

    sp = getattr(flt, "_second_pass", None)
    sp_info = None
    if sp is not None and sp.is_active:
        sp_info = {
            "active": True,
            "models": list(getattr(sp._manager, "modules", {}).keys()),
            "threshold": sp.config.threshold,
        }
    else:
        sp_info = {"active": False}

    return {
        "sdk_version": __version__,
        "dictionary_size": flt.get_dictionary_size(),
        "security_level": flt.security_level.value,
        "second_pass": sp_info,
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

    result = flt.analyze(
        req.text,
        whitelist=req.whitelist,
        blacklist=req.blacklist,
        use_second_pass=req.use_ai_filter,
    )
    return _to_response(result)


@app.post("/analyze/batch", response_model=list[AnalyzeResponse])
async def analyze_batch(
    req: BatchRequest,
    flt: Annotated[NervFilter, Depends(get_filter)],
):
    if req.security_level != flt.security_level:
        flt.security_level = req.security_level

    results = flt.analyze_batch(
        req.texts,
        whitelist=req.whitelist,
        blacklist=req.blacklist,
        use_second_pass=req.use_ai_filter,
    )
    return [_to_response(r) for r in results]


@app.post("/train-one", response_model=TrainOneResponse)
async def train_one(
    req: TrainOneRequest,
    flt: Annotated[NervFilter, Depends(get_filter)],
):
    """2차 모듈 head 를 단일 샘플로 즉시 업데이트.

    재학습 큐를 거치지 않고 즉시 학습 → 운영 환경에서는 사용 신중.
    """
    sp = getattr(flt, "_second_pass", None)
    if sp is None or not sp.is_active:
        raise HTTPException(status_code=503, detail="2차 필터가 활성화되지 않았습니다.")
    try:
        result = sp.update(req.module_name, req.text, req.label, save=req.save)
        return TrainOneResponse(
            module=result["module"],
            loss=result["loss"],
            score_after_step=result["score_after_step"],
            saved=req.save,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실시간 학습 중 오류: {e}")
