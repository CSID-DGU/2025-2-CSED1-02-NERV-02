from enum import Enum


class ListType(str, Enum):
    """사전 타입 (whitelist/blacklist)"""
    WHITELIST = "WHITELIST"
    BLACKLIST = "BLACKLIST"


class SecurityLevel(str, Enum):
    """유저 보안 모드 (3단계)"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ModerationAction(str, Enum):
    """댓글 최종 처분 액션 (4색 체계)"""
    NORMAL = "NORMAL"               # 🟢 정상 (통과)
    REVIEW = "REVIEW"               # 🟡 경고/사용자 검토
    PARTIAL_MASK = "PARTIAL_MASK"   # 🟠 부분 마스킹
    FULL_BLOCK = "FULL_BLOCK"       # 🔴 완전 차단
    ERROR = "ERROR"


class KeywordMode(str, Enum):
    """영상 내 빈도 키워드에 대한 유저 선택 모드"""
    IGNORE = "IGNORE"     # 기본: no-op (백엔드에 아무 효과 없음)
    FILTER = "FILTER"     # 키워드 자체를 블랙리스트처럼 필터링
    TRIGGER = "TRIGGER"   # 욕설과 동시 등장 시 강한 처분 유도


class FilterStatus(str, Enum):
    """필터링 파이프라인 상태"""
    PASSED = "PASSED"
    FILTERED_BY_FIRST_PASS = "FILTERED_BY_FIRST_PASS"
    FILTERED_BY_SECOND_PASS = "FILTERED_BY_SECOND_PASS"


class WordType(str, Enum):
    """감지 단어의 출처 유형"""
    WHITELIST = "WHITELIST"
    USER_BLACKLIST = "USER_BLACKLIST"
    SYSTEM_KEYWORD = "SYSTEM_KEYWORD"
    AI_BASIC = "AI_BASIC"
