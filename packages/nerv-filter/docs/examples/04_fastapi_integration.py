"""FastAPI 통합 예시 — 단일 인스턴스를 lifespan 으로 공유.

실행:
    pip install fastapi uvicorn
    uvicorn 04_fastapi_integration:app --reload

테스트:
    curl -X POST http://localhost:8000/analyze \\
        -H "Content-Type: application/json" \\
        -d '{"text": "이 시발 새끼야"}'
"""
from contextlib import asynccontextmanager

# Note: 실행을 위해 fastapi 설치 필요
# 이 파일은 pip install fastapi uvicorn 후 실행 가능합니다.
try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except ImportError:
    print("이 예제는 fastapi와 pydantic이 필요합니다:")
    print("  pip install fastapi uvicorn")
    raise SystemExit(1)

from nerv_filter import NervFilter, SecurityLevel


# 애플리케이션 lifespan 동안 NervFilter 1개만 유지 (Kiwi 로딩 절약)
_filter: NervFilter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _filter
    _filter = NervFilter(security_level=SecurityLevel.MEDIUM)
    print(f"NervFilter 초기화 완료 (사전 {_filter.get_dictionary_size():,}건)")
    yield
    # cleanup (필요 없음)


app = FastAPI(title="nerv-filter demo", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    text: str
    security_level: str = "MEDIUM"


class AnalyzeResponse(BaseModel):
    action: str
    masked_text: str
    score: float
    detected_words: list[dict]
    flags: dict


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    # 보안 수준이 다르면 임시로 변경
    assert _filter is not None
    original_level = _filter.security_level
    if req.security_level != original_level.value:
        _filter.security_level = SecurityLevel(req.security_level)

    # 비동기 wrapper 사용
    result = await _filter.analyze_async(req.text)

    # 원래대로 복귀
    if req.security_level != original_level.value:
        _filter.security_level = original_level

    return AnalyzeResponse(
        action=result.action.value,
        masked_text=result.masked_text,
        score=result.score,
        detected_words=[
            {"word": d.word, "type": d.word_type.value} for d in result.detected_words
        ],
        flags={
            "has_blacklist": result.flags.has_blacklist,
            "has_general": result.flags.has_general,
            "has_trigger": result.flags.has_trigger,
        },
    )


@app.post("/analyze/batch")
async def analyze_batch(texts: list[str]):
    assert _filter is not None
    results = _filter.analyze_batch(texts)
    return [r.to_dict() for r in results]


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "dictionary_size": _filter.get_dictionary_size() if _filter else 0,
    }
