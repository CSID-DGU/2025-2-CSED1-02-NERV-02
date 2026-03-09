import os
from typing import Optional, Dict, List
from dotenv import load_dotenv

load_dotenv()

def load_enabled_modules(all_modules: Dict[str, str]) -> Dict[str, str]:
    """환경변수에 따라 활성화된 모듈만 반환"""
    enabled = os.getenv("ENABLED_MODULES", "ALL")
    
    if enabled.upper() == "ALL":
        return all_modules.copy()
    
    selected = [k.strip().upper() for k in enabled.split(',') if k.strip()]
    return {k: v for k, v in all_modules.items() if k in selected}

class Config:

    # ===== 시스템 설정 =====
    SECURITY_LEVEL: int = int(os.getenv("SECURITY_LEVEL", 3))
    """ 보안 레벨 (1:관찰 ~ 5:최대보호)"""

    USE_DETAIL_AI_MODEL: bool = os.getenv("USE_DETAIL_AI_MODEL", "False").lower() == "true"
    """2차 특수 AI 모델 사용 여부"""

    RISK_THRESHOLD: float = float(os.getenv("RISK_THRESHOLD", 0.65))
    """필터링 임계값 (0.0 ~ 1.0)"""
    
    BASIC_THRESHOLD: float = float(os.getenv("BASIC_THRESHOLD", 0.9))
    """Basic AI 모듈 임계값 (0.0 ~ 1.0)"""

    # ===== API 키 =====
    YOUTUBE_API_KEY: Optional[str] = os.getenv("YOUTUBE_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # ===== 기본 AI 모듈 =====
    BASIC_AI_MODULE = [
        '공격적이거나 모욕적인 내용이 포함되어 있는지',
        '사회적 통념상 용인되기 어려운 혐오 표현이 있는지'
    ]

    # ===== 특수 AI 모듈 정의 =====
    _SPECIAL_AI_MODULE_DEFINITIONS: Dict[str, str] = {
        'MODIFIED': '자음/모음 분리(예: ㅂㅅ), 특수문자 삽입, 야민정음 등 필터링 회피 시도',
        'SEXUAL': '성적 수치심 유발, 음란한 묘사, 성희롱',
        'PRIVACY': '전화번호, 주소, 실명, 계좌번호 등 개인정보 유출',
        'AGGRESSION': '특정 대상에 대한 맹목적 비난, 살해 협박, 저주',
        'POLITICAL': '영상 맥락과 무관한 정치적 선동, 혐오 발언',
        'SPAM': '광고, 도배, 무의미한 문자열 반복',
        'FAMILY': '가족(부모, 자녀 등)을 비하하거나 모욕하는 패륜적 발언'
    }

    # ===== 특수 AI 모듈 로드 =====            
    SPECIAL_AI_MODULES: Dict[str, str] = load_enabled_modules(_SPECIAL_AI_MODULE_DEFINITIONS)

    # ===== 검증 =====
    @classmethod
    def validate(cls) -> bool:
        errors = []

        if not cls.YOUTUBE_API_KEY: errors.append("❌ YOUTUBE_API_KEY 설정 필요 (.env 파일 확인)")
        if not cls.OPENAI_API_KEY: errors.append("❌ OPENAI_API_KEY 설정 필요 (.env 파일 확인)")
        if not (1 <= cls.SECURITY_LEVEL <= 5): errors.append(f"❌ SECURITY_LEVEL은 1-5 사이여야 함 (현재: {cls.SECURITY_LEVEL})")
        
        if errors: raise ValueError("\n".join(errors))
        
        print("✅ 설정 검증 완료")
        return True
    
    @classmethod
    def print_config(cls):
        """설정 출력 (앱 시작 시 확인용)"""
        print("\n" + "="*50)
        print("📋 YouTube Comment Filter - 현재 설정")
        print("="*50)
        print(f"  보안 레벨: {cls.SECURITY_LEVEL}")
        print(f"  위험도 임계값: {cls.RISK_THRESHOLD}")
        print(f"  Basic AI 모듈 임계값: {cls.BASIC_THRESHOLD}")
        print(f"  특수 AI 모듈: {'사용' if cls.USE_DETAIL_AI_MODEL else '미사용'}")
        print(f"  활성 특수 AI 모듈: {list(cls.SPECIAL_AI_MODULES.keys())}")
        print(f"  YouTube API: {'설정됨' if cls.YOUTUBE_API_KEY else '❌ 미설정'}")
        print(f"  OpenAI API: {'설정됨' if cls.OPENAI_API_KEY else '❌ 미설정'}")
        print("="*50 + "\n")

config = Config()

if __name__ == "__main__":
    try:
        config.validate()
        config.print_config()
        print("✅ config.py 정상 동작")
    except ValueError as e:
        print(e)