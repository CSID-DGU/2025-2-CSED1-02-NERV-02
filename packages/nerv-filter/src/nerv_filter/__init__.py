"""nerv-filter — Korean profanity filter with morphological analysis.

Quick start:
    >>> from nerv_filter import filter_text
    >>> result = filter_text("이 시발 새끼야")
    >>> print(result.action)

Or for repeated use, prefer instance reuse:
    >>> from nerv_filter import NervFilter
    >>> flt = NervFilter()
    >>> for text in many_texts:
    ...     result = flt.analyze(text)

See https://github.com/CSID-DGU/2025-2-CSED1-02-NERV-02 for details.
"""
from __future__ import annotations

from ._version import __version__
from .core.engine import NervFilter
from .exceptions import (
    ConfigError,
    DictionaryError,
    EngineError,
    NervFilterError,
)
from .models import (
    DetectedWord,
    FilterResult,
    FilterStatus,
    ModerationAction,
    ScorerFlags,
    SecurityLevel,
    WordType,
)

# 함수형 1줄 사용 — 내부적으로 싱글톤 인스턴스 재사용
_default_filters: dict[SecurityLevel, NervFilter] = {}


def filter_text(
    text: str,
    security_level: SecurityLevel = SecurityLevel.MEDIUM,
) -> FilterResult:
    """1줄 사용 편의 함수.

    동일 ``security_level`` 의 NervFilter 인스턴스를 캐싱해 재사용한다.
    반복 호출 시 Kiwi 재로딩 오버헤드 없음.

    Args:
        text: 분석할 텍스트.
        security_level: 정책 강도. 기본 ``MEDIUM``.

    Returns:
        FilterResult.
    """
    if security_level not in _default_filters:
        _default_filters[security_level] = NervFilter(security_level=security_level)
    return _default_filters[security_level].analyze(text)


__all__ = [
    "NervFilter",
    "filter_text",
    "SecurityLevel",
    "ModerationAction",
    "FilterResult",
    "DetectedWord",
    "ScorerFlags",
    "FilterStatus",
    "WordType",
    "NervFilterError",
    "DictionaryError",
    "ConfigError",
    "EngineError",
    "__version__",
]
