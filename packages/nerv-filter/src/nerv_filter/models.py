"""nerv-filter 공개 데이터 모델.

Pydantic 의존을 제거하고 표준 라이브러리 dataclass + Enum 만 사용한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SecurityLevel(str, Enum):
    """필터 정책 강도. 같은 입력이라도 단계가 높을수록 더 강한 처분이 적용된다."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ModerationAction(str, Enum):
    """필터링 결과로 적용할 처분 액션."""

    NORMAL = "NORMAL"               # 정상 (통과)
    REVIEW = "REVIEW"               # 사용자 검토 권고
    PARTIAL_MASK = "PARTIAL_MASK"   # 부분 마스킹
    FULL_BLOCK = "FULL_BLOCK"       # 완전 차단
    ERROR = "ERROR"


class WordType(str, Enum):
    """탐지 단어의 출처 분류."""

    WHITELIST = "WHITELIST"
    USER_BLACKLIST = "USER_BLACKLIST"
    SYSTEM_KEYWORD = "SYSTEM_KEYWORD"
    AI_BASIC = "AI_BASIC"


class FilterStatus(str, Enum):
    """필터 파이프라인 진행 상태."""

    PASSED = "PASSED"
    FILTERED_BY_FIRST_PASS = "FILTERED_BY_FIRST_PASS"
    FILTERED_BY_SECOND_PASS = "FILTERED_BY_SECOND_PASS"


@dataclass(frozen=True)
class DetectedWord:
    """매칭된 단어 1건."""

    word: str
    word_type: WordType


@dataclass(frozen=True)
class ScorerFlags:
    """매칭 결과 플래그 — 정책 결정의 입력으로 쓰인다."""

    has_blacklist: bool
    has_general: bool
    has_trigger: bool


@dataclass(frozen=True)
class FilterResult:
    """필터링 최종 결과.

    - ``original_text``: 입력 텍스트 원본
    - ``masked_text``: 마스킹/차단이 적용된 결과 (action 에 따라 달라짐)
    - ``action``: 적용된 처분
    - ``score``: 0.0 ~ 1.0 위험도
    - ``detected_words``: 매칭된 단어 목록
    - ``flags``: 카테고리 플래그
    """

    original_text: str
    masked_text: str
    action: ModerationAction
    score: float
    detected_words: list[DetectedWord] = field(default_factory=list)
    flags: ScorerFlags = field(default_factory=lambda: ScorerFlags(False, False, False))

    @property
    def is_clean(self) -> bool:
        """필터에 걸리지 않은 정상 텍스트인지."""
        return self.action == ModerationAction.NORMAL

    @property
    def is_blocked(self) -> bool:
        """완전 차단된 텍스트인지."""
        return self.action == ModerationAction.FULL_BLOCK

    def to_dict(self) -> dict:
        """JSON 직렬화 편의."""
        return {
            "original_text": self.original_text,
            "masked_text": self.masked_text,
            "action": self.action.value,
            "score": self.score,
            "detected_words": [
                {"word": d.word, "type": d.word_type.value}
                for d in self.detected_words
            ],
            "flags": {
                "has_blacklist": self.flags.has_blacklist,
                "has_general": self.flags.has_general,
                "has_trigger": self.flags.has_trigger,
            },
        }
