import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List

logger = logging.getLogger(__name__)

class Settings(BaseSettings):

    DATABASE_URL: str
    YOUTUBE_API_KEY: str
    OPENAI_API_KEY: str

    DEBUG_MODE: bool = False

    BASIC_AI_MODULE: List[str] = [
        '공격적이거나 모욕적인 내용이 포함되어 있는지',
        '사회적 통념상 용인되기 어려운 혐오 표현이 있는지'
    ]

    _SPECIAL_AI_MODULE_DEFINITIONS: Dict[str, str] = {
        'MODIFIED': '자음/모음 분리(예: ㅂㅅ), 특수문자 삽입, 야민정음 등 필터링 회피 시도',
        'SEXUAL': '성적 수치심 유발, 음란한 묘사, 성희롱',
        'PRIVACY': '전화번호, 주소, 실명, 계좌번호 등 개인정보 유출',
        'AGGRESSION': '특정 대상에 대한 맹목적 비난, 살해 협박, 저주',
        'POLITICAL': '영상 맥락과 무관한 정치적 선동, 혐오 발언',
        'SPAM': '광고, 도배, 무의미한 문자열 반복',
        'FAMILY': '가족(부모, 자녀 등)을 비하하거나 모욕하는 패륜적 발언'
    }

    # SecondPassFilter 등에서 사용할 수 있도록 프로퍼티로 노출
    @property
    def SPECIAL_AI_MODULES(self) -> Dict[str, str]:
        """AI 필터링 특수 모듈 정의 (카테고리별 규칙)"""
        return self._SPECIAL_AI_MODULE_DEFINITIONS

    # 기본 임계값 (SecondPassFilter에서 필요)
    BASIC_THRESHOLD: float = 0.9

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()