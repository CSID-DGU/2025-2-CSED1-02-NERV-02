from typing import List, Dict
from pydantic import BaseModel, Field

# [Raw Text]

class TextAnalysisRequest(BaseModel):
    """단일 텍스트 분석 요청"""
    text: str = Field(..., json_schema_extra={
        "example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
    })

# [1차 필터링 결과 모델]

class FirstPassDetectedWord(BaseModel):
    """1차 필터 감지 단어"""
    word: str = Field(..., description="1차 필터가 잡아낸 단어", json_schema_extra={"example": "개새끼"})
    type: str = Field(..., description="감지 유형 (시스템/사용자 사전)", json_schema_extra={"example": "SYSTEM_KEYWORD"})

class FirstPassResponse(BaseModel):
    """1차 필터링 응답"""
    original_text: str = Field(..., json_schema_extra={"example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"})
    status: str = Field(..., description="1차 필터링 상태", json_schema_extra={"example": "FILTERED_BY_FIRST_PASS"})
    detected_words: List[FirstPassDetectedWord] = Field(..., json_schema_extra={
        "example": [{"word": "개새끼", "type": "SYSTEM_KEYWORD"}]
    })
    masked_text: str = Field(..., description="1차 마스킹 완료된 텍스트", json_schema_extra={
        "example": "야이 __F__야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
    })

# [2차 필터링 결과 모델]

class SecondPassDetectedWord(BaseModel):
    """2차 필터 감지 단어"""
    word: str = Field(..., description="1차 혹은 2차 필터가 잡아낸 단어", json_schema_extra={"example": "010-1234-5678"})
    type: str = Field(..., description="감지 유형 (AI 카테고리 포함)", json_schema_extra={"example": "AI_PRIVACY"})

class SecondPassResponse(BaseModel):
    """2차 필터링 응답"""
    original_text: str = Field(..., json_schema_extra={"example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"})
    status: str = Field(..., description="2차 필터링 상태 (누적)", json_schema_extra={"example": "FILTERED_BY_SECOND_PASS"})
    detected_words: List[SecondPassDetectedWord] = Field(..., description="1차+2차 누적 적발 리스트", json_schema_extra={
        "example": [
            {"word": "개새끼", "type": "SYSTEM_KEYWORD"},
            {"word": "니네 집 주소 다 털었다", "type": "AI_AGGRESSION"},
            {"word": "010-1234-5678", "type": "AI_PRIVACY"}
        ]
    })
    masked_text: str = Field(..., description="2차 마스킹 완료된 텍스트", json_schema_extra={
        "example": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
    })

# [위험도 계산 및 정책 모델]

class RiskResponse(BaseModel):
    """위험도 계산 응답"""
    risk_score: float = Field(..., description="0.0 ~ 1.0 사이의 위험도 점수", json_schema_extra={"example": 0.98})

class PolicyRequest(BaseModel):
    """정책 결정 요청"""
    risk_score: float = Field(..., json_schema_extra={"example": 0.98})
    filter_result: SecondPassResponse 

class PolicyResponse(BaseModel):
    """정책 결정 응답"""
    action: str = Field(..., description="최종 처분 결과", json_schema_extra={"example": "AUTO_HIDE"})
    processed_text: str = Field(..., description="최종 노출 텍스트", json_schema_extra={"example": "규정 위반으로 숨겨진 메시지입니다."})
    score: float = Field(..., json_schema_extra={"example": 0.98})

# [통합 결과 모델]

class AnalysisResult(BaseModel):
    """분석 최종 결과"""
    original_text: str
    processed_text: str
    action: str
    score: float
    details: SecondPassResponse

# [유튜브 리포트 모델]

class YoutubeCommentSummary(BaseModel):
    """유튜브 댓글 요약"""
    author: str
    published_at: str
    original: str
    processed: str
    action: str
    risk_score: float
    violation_tags: List[str]

class YoutubeAnalysisRequest(BaseModel):
    """유튜브 영상 분석 요청"""
    video_id: str
    max_pages: int = 1

class YoutubeAnalysisResponse(BaseModel):
    """유튜브 영상 분석 응답"""
    video_info: Dict[str, str]
    stats: Dict[str, int]
    results: List[YoutubeCommentSummary]