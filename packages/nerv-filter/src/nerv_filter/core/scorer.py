"""위험도 점수 계산기.

3-bucket 스펙. 보안수준 비의존적 base score 만 계산한다.
PolicyManager 가 이 결과로 액션을 결정한다.

Bucket:
- Normal  0~25  : 검출 단어 없음 (초성+특수문자 비율 기반)
- Caution 26~50 : SYSTEM 사전만 검출
- Warn    51~75 : BLACKLIST 검출 포함
+ trigger: +25
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from ..models import WordType

logger = logging.getLogger(__name__)


_HANGUL_CONSONANT_START = 0x3131
_HANGUL_CONSONANT_END = 0x314E
_HANGUL_VOWEL_START = 0x314F
_HANGUL_VOWEL_END = 0x3163
_HANGUL_SYLLABLE_START = 0xAC00
_HANGUL_SYLLABLE_END = 0xD7A3


def _is_standalone_consonant(ch: str) -> bool:
    return _HANGUL_CONSONANT_START <= ord(ch) <= _HANGUL_CONSONANT_END


def _is_hangul_syllable(ch: str) -> bool:
    return _HANGUL_SYLLABLE_START <= ord(ch) <= _HANGUL_SYLLABLE_END


def _is_standalone_vowel(ch: str) -> bool:
    return _HANGUL_VOWEL_START <= ord(ch) <= _HANGUL_VOWEL_END


def _is_special_char(ch: str) -> bool:
    if ch.isspace():
        return False
    if _is_hangul_syllable(ch):
        return False
    if ch.isalnum():
        return False
    if _is_standalone_consonant(ch) or _is_standalone_vowel(ch):
        return False
    return True


class RiskScorer:
    """필터 결과 → 위험도 점수.

    SDK 공개 API 는 아님. NervFilter 내부에서 사용.
    """

    def __init__(self) -> None:
        logger.debug("[nerv_filter] RiskScorer 로드")

    def execute(
        self,
        filter_result: Dict[str, Any],
        trigger_keywords: frozenset[str] | None = None,
    ) -> Dict[str, Any]:
        triggers = trigger_keywords or frozenset()

        detected_words = filter_result.get("detected_words", [])
        original_text = filter_result.get("original_text", "")

        has_blacklist = any(
            item["type"] == WordType.USER_BLACKLIST for item in detected_words
        )
        has_system = any(
            item["type"] == WordType.SYSTEM_KEYWORD for item in detected_words
        )

        text_has_trigger = any(kw and kw in original_text for kw in triggers)
        has_trigger = (has_system or has_blacklist) and text_has_trigger

        non_space_len = sum(1 for c in original_text if not c.isspace())

        if not detected_words:
            score_100 = self._normal_bucket(original_text, non_space_len)
            return self._pack(score_100, False, False, False)

        if not has_blacklist:
            detected_len = sum(len(item.get("word", "")) for item in detected_words)
            score_100 = self._caution_bucket(detected_len, non_space_len)
            if has_trigger:
                score_100 += 25.0
        else:
            detected_len = sum(len(item.get("word", "")) for item in detected_words)
            score_100 = self._warn_bucket(detected_len, non_space_len)
            if has_trigger:
                score_100 += 25.0

        return self._pack(score_100, has_blacklist, has_system, has_trigger)

    @staticmethod
    def _normal_bucket(text: str, non_space_len: int) -> float:
        if non_space_len <= 0:
            return 0.0
        cho = sum(1 for c in text if _is_standalone_consonant(c))
        spec = sum(1 for c in text if _is_special_char(c))
        ratio = (cho + spec) / non_space_len
        clamped = min(ratio, 0.33)
        return round(clamped / 0.33 * 25.0, 2)

    @staticmethod
    def _caution_bucket(detected_len: int, non_space_len: int) -> float:
        if non_space_len <= 0:
            return 26.0
        ratio = detected_len / non_space_len
        clamped = max(0.10, min(ratio, 1.0))
        return 26.0 + (clamped - 0.10) / 0.90 * (50.0 - 26.0)

    @staticmethod
    def _warn_bucket(detected_len: int, non_space_len: int) -> float:
        if non_space_len <= 0:
            return 51.0
        ratio = detected_len / non_space_len
        clamped = max(0.10, min(ratio, 1.0))
        return 51.0 + (clamped - 0.10) / 0.90 * (75.0 - 51.0)

    @staticmethod
    def _pack(
        score_100: float,
        has_blacklist: bool,
        has_system: bool,
        has_trigger: bool,
    ) -> Dict[str, Any]:
        score_100 = max(0.0, min(score_100, 100.0))
        return {
            "score": round(score_100 / 100.0, 2),
            "has_blacklist": has_blacklist,
            "has_general": has_system,
            "has_trigger": has_trigger,
        }
