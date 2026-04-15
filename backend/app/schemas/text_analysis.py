from pydantic import BaseModel, Field
from app.schemas.enums import FilterStatus, WordType, ModerationAction

# [Raw Text]

class TextAnalysisRequest(BaseModel):
    """단일 텍스트 분석 요청"""
    text: str = Field(..., json_schema_extra={
        "example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
    })

# [필터링 결과 모델]

class DetectedWord(BaseModel):
    """탐지된 단어"""
    word: str = Field(..., description="필터가 잡아낸 단어", json_schema_extra={"example": "개새끼"})
    type: WordType = Field(..., description="감지 유형 (시스템/사용자 사전)", json_schema_extra={"example": "SYSTEM_KEYWORD"})


class FilterResult(BaseModel):
    """텍스트 분석 응답"""
    original_text: str = Field(..., json_schema_extra={"example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"})
    status: FilterStatus = Field(..., description="1차 필터링 상태", json_schema_extra={"example": "FILTERED_BY_FIRST_PASS"})
    detected_words: list[DetectedWord] = Field(..., json_schema_extra={
        "example": [{"word": "개새끼", "type": "SYSTEM_KEYWORD"}]
    })
    masked_text: str = Field(..., description="1차 마스킹 완료된 텍스트", json_schema_extra={
        "example": "야이 __F__야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
    })

# [위험도 계산 및 정책 모델]

class RiskResponse(BaseModel):
    """위험도 계산 응답"""
    risk_score: float = Field(..., description="0.0 ~ 1.0 사이의 위험도 점수", json_schema_extra={"example": 0.98})

class PolicyRequest(BaseModel):
    """정책 결정 요청"""
    risk_score: float = Field(..., json_schema_extra={"example": 0.98})
    filter_result: FilterResult = Field(...)

class PolicyResponse(BaseModel):
    """정책 결정 응답"""
    action: ModerationAction = Field(..., description="최종 처분 결과", json_schema_extra={"example": "FULL_BLOCK"})
    processed_text: str = Field(..., description="최종 노출 텍스트", json_schema_extra={"example": "야이 *** ㅋㅋ ..."})
    score: float = Field(..., json_schema_extra={"example": 0.98})

# [통합 결과 모델]

class ScorerFlags(BaseModel):
    """RiskScorer가 반환하는 카테고리 플래그. 프론트엔드가 보안 모드 변경 시
    서버 재호출 없이 action/processed_text를 재유도할 수 있도록 노출한다."""
    has_blacklist: bool = False
    has_general: bool = False
    has_trigger: bool = False


class TextAnalysisResponse(BaseModel):
    """분석 최종 결과"""
    original_text: str
    processed_text: str
    action: ModerationAction
    score: float
    details: FilterResult
    flags: ScorerFlags