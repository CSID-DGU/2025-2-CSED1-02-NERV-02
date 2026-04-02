from enum import Enum


class ListType(str, Enum):
    """사전 타입 (whitelist/blacklist)"""
    WHITELIST = "WHITELIST"
    BLACKLIST = "BLACKLIST"


class ModerationAction(str, Enum):
    """댓글 최종 처분 액션"""
    PASS = "PASS"
    MASKING = "MASKING"
    REVIEW_HUMAN = "REVIEW_HUMAN"
    AUTO_HIDE = "AUTO_HIDE"
    PERMANENT_DELETE = "PERMANENT_DELETE"
    ERROR = "ERROR"


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