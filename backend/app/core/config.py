import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List

logger = logging.getLogger(__name__)

class Settings(BaseSettings):

    DATABASE_URL: str
    YOUTUBE_API_KEY: str
    OPENAI_API_KEY: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DEBUG_MODE: bool = False
    VIDEO_ANALYSIS_CACHE_TTL_SECONDS: int = 3600
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    HF_TOKEN: str
    HF_MODEL_OWNER: str
    
    _SPECIAL_AI_MODULE_DEFINITIONS: Dict[str, str] = {
        'BASIC': '1차에서 잡지 못한 기본 욕설(회피 포함)',
        'SEXUAL': '성적 수치심 유발, 음란한 묘사, 성희롱',
        'PII': '전화번호, 주소, 실명, 계좌번호 등 개인정보 유출',
        'CRITICISM': '특정 대상에 대한 맹목적 비난, 살해 협박, 저주',
        'POLITICS': '영상 맥락과 무관한 정치적 선동, 혐오 발언',
        'SPAM': '광고, 도배, 무의미한 문자열 반복',
        'FAMILY': '가족(부모, 자녀 등)을 비하하거나 모욕하는 패륜적 발언'
    }

    # SecondPassFilter 등에서 사용할 수 있도록 프로퍼티로 노출
    @property
    def SPECIAL_AI_MODULES(self) -> Dict[str, str]:
        """AI 필터링 특수 모듈 정의 (카테고리별 규칙)"""
        return self._SPECIAL_AI_MODULE_DEFINITIONS

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
