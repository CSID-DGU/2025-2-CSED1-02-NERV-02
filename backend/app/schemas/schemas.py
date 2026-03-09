from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# [사전 관리 모델]

class DictionaryRequest(BaseModel):
    words: List[str] = Field(..., description="추가/삭제할 단어 리스트", json_schema_extra={"example": ["바보", "멍청이"]})
    list_type: str = Field(..., description="'whitelist' 또는 'blacklist'", json_schema_extra={"example": "blacklist"})

class DictionaryResponse(BaseModel):
    whitelist: List[str] = Field(default_factory=list, description="허용 단어 목록")
    blacklist: List[str] = Field(default_factory=list, description="차단 단어 목록")
    total_count: int = Field(..., description="조회된 총 단어 수")

class DictionaryUpdateResponse(BaseModel):
    status: str
    message: str
    processed_count: int
    current_total: Dict[str, int]

# [시스템 설정 모델]

class SystemConfigUpdate(BaseModel):
    security_level: Optional[int] = Field(None, description="보안 레벨 (1~5)", ge=1, le=5, json_schema_extra={"example": 4})
    risk_threshold: Optional[float] = Field(None, description="위험도 임계값 (0.0~1.0)", ge=0.0, le=1.0, json_schema_extra={"example": 0.75})
    use_detail_ai: Optional[bool] = Field(None, description="2차 정밀 AI 모델 사용 여부", json_schema_extra={"example": True})
    enabled_modules: Optional[List[str]] = Field(None, description="활성화할 AI 모듈 키 리스트", json_schema_extra={"example": ["SEXUAL", "PRIVACY", "AGGRESSION"]})

class SystemConfigResponse(BaseModel):
    security_level: int
    risk_threshold: float
    use_detail_ai_model: bool
    enabled_modules: List[str]

# --- [Raw Text] ---

class TextInput(BaseModel):
    text: str = Field(..., json_schema_extra={
        "example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
    })

# --- [1차 필터링 결과 모델] ---

class FirstPassDetectedWord(BaseModel):
    word: str = Field(..., description="1차 필터가 잡아낸 단어", json_schema_extra={"example": "개새끼"})
    type: str = Field(..., description="감지 유형 (시스템/사용자 사전)", json_schema_extra={"example": "SYSTEM_KEYWORD"})

class FirstPassResponse(BaseModel):
    original_text: str = Field(..., json_schema_extra={"example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"})
    status: str = Field(..., description="1차 필터링 상태", json_schema_extra={"example": "FILTERED_BY_FIRST_PASS"})
    detected_words: List[FirstPassDetectedWord] = Field(..., json_schema_extra={
        "example": [{"word": "개새끼", "type": "SYSTEM_KEYWORD"}]
    })
    text_for_filtering: str = Field(..., description="1차 마스킹 완료된 텍스트", json_schema_extra={
        "example": "야이 __F__야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
    })

# --- [2차 필터링 결과 모델] ---

class SecondPassDetectedWord(BaseModel):
    word: str = Field(..., description="1차 혹은 2차 필터가 잡아낸 단어", json_schema_extra={"example": "010-1234-5678"})
    type: str = Field(..., description="감지 유형 (AI 카테고리 포함)", json_schema_extra={"example": "AI_PRIVACY"})

class SecondPassResponse(BaseModel):
    original_text: str = Field(..., json_schema_extra={"example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"})
    status: str = Field(..., description="2차 필터링 상태 (누적)", json_schema_extra={"example": "FILTERED_BY_SECOND_PASS"})
    detected_words: List[SecondPassDetectedWord] = Field(..., description="1차+2차 누적 적발 리스트", json_schema_extra={
        "example": [
            {"word": "개새끼", "type": "SYSTEM_KEYWORD"},
            {"word": "니네 집 주소 다 털었다", "type": "AI_AGGRESSION"},
            {"word": "010-1234-5678", "type": "AI_PRIVACY"}
        ]
    })
    text_for_filtering: str = Field(..., description="2차 마스킹 완료된 텍스트", json_schema_extra={
        "example": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
    })

# --- [위험도 계산 및 정책 모델] ---

class RiskResponse(BaseModel):
    risk_score: float = Field(..., description="0.0 ~ 1.0 사이의 위험도 점수", json_schema_extra={"example": 0.98})

class PolicyInput(BaseModel):
    risk_score: float = Field(..., json_schema_extra={"example": 0.98})
    # 정책 결정에는 최종 결과(2차 결과)가 들어가는 것이 맞음
    filter_result: SecondPassResponse 

class PolicyResponse(BaseModel):
    action: str = Field(..., description="최종 처분 결과", json_schema_extra={"example": "AUTO_HIDE"})
    processed_text: str = Field(..., description="최종 노출 텍스트", json_schema_extra={"example": "규정 위반으로 숨겨진 메시지입니다."})
    score: float = Field(..., json_schema_extra={"example": 0.98})

# --- [통합 결과 모델] ---

class AnalysisResult(BaseModel):
    original_text: str
    processed_text: str
    action: str
    score: float
    details: SecondPassResponse # 디테일은 최종 필터링 결과 구조를 따름

# --- [유튜브 리포트 모델] ---

class YoutubeCommentSummary(BaseModel):
    author: str
    published_at: str
    original: str
    processed: str
    action: str
    risk_score: float
    violation_tags: List[str]

class YoutubeAnalysisResponse(BaseModel):
    video_info: Dict[str, str]
    stats: Dict[str, int]
    results: List[YoutubeCommentSummary]