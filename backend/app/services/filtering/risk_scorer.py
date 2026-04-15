"""
위험도 점수 계산기 (4-bucket 스펙, security-level 비의존 base score).

서버는 보안수준과 무관한 base score 만 계산한다. 보안수준(+25) 보정은
클라이언트 derivePolicy 에서 즉시 적용되어, 보안 설정 변경 시 서버 재호출
없이 점수가 반응하도록 한다.

Bucket 분포 (server base):
  - Normal  0~25  : 검출 단어 없음. (초성 + 특수문자) / 비공백 길이 비율.
                    0% → 0, 33%+ → 25 (선형)
  - Caution 26~50 : SYSTEM 사전 키워드만 검출.
                    10%↓ → 26, 100% → 50 (선형)
                    +25 if trigger
  - Warn    51~75 : BLACKLIST 키워드 검출.
                    10%↓ → 51, 100% → 75 (선형)
                    +25 if trigger

최종 score 는 0~1 float. PolicyManager/derivePolicy 는 flags 로 action 을
결정하고, 클라이언트에서 보안수준 가산을 적용하여 display score 를 완성한다.
"""
import logging
from typing import Dict, Any

from app.schemas.enums import WordType
from .context import VideoContext

logger = logging.getLogger(__name__)


_HANGUL_CONSONANT_START = 0x3131  # ㄱ
_HANGUL_CONSONANT_END = 0x314E    # ㅎ
_HANGUL_VOWEL_START = 0x314F      # ㅏ
_HANGUL_VOWEL_END = 0x3163        # ㅣ
_HANGUL_SYLLABLE_START = 0xAC00   # 가
_HANGUL_SYLLABLE_END = 0xD7A3     # 힣


def _is_standalone_consonant(ch: str) -> bool:
    return _HANGUL_CONSONANT_START <= ord(ch) <= _HANGUL_CONSONANT_END


def _is_hangul_syllable(ch: str) -> bool:
    return _HANGUL_SYLLABLE_START <= ord(ch) <= _HANGUL_SYLLABLE_END


def _is_standalone_vowel(ch: str) -> bool:
    return _HANGUL_VOWEL_START <= ord(ch) <= _HANGUL_VOWEL_END


def _is_special_char(ch: str) -> bool:
    """공백/한글음절/영숫자/한글자모를 제외한 모든 문자."""
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
    def __init__(self):
        logger.info("[System] Risk Scorer(위험도 분석기) 로드 완료")

    def execute(
        self,
        filter_result: Dict[str, Any],
        video_context: VideoContext | None = None,
    ) -> Dict[str, Any]:
        ctx = video_context or VideoContext()

        detected_words = filter_result.get("detected_words", [])
        original_text = filter_result.get("original_text", "")

        has_blacklist = any(
            item["type"] == WordType.USER_BLACKLIST for item in detected_words
        )
        has_system = any(
            item["type"] == WordType.SYSTEM_KEYWORD for item in detected_words
        )

        text_has_trigger = any(kw and kw in original_text for kw in ctx.trigger_keywords)
        has_trigger = (has_system or has_blacklist) and text_has_trigger

        non_space_len = sum(1 for c in original_text if not c.isspace())

        # ── Normal: 검출 없음 ──
        if not detected_words:
            score_100 = self._normal_bucket(original_text, non_space_len)
            return self._pack(score_100, False, False, False)

        # ── Caution: SYSTEM 전용 ──
        if not has_blacklist:
            detected_len = sum(len(item.get("word", "")) for item in detected_words)
            score_100 = self._caution_bucket(detected_len, non_space_len)
            if has_trigger:
                score_100 += 25.0

        # ── Warn: BLACKLIST 포함 ──
        else:
            detected_len = sum(len(item.get("word", "")) for item in detected_words)
            score_100 = self._warn_bucket(detected_len, non_space_len)
            if has_trigger:
                score_100 += 25.0

        return self._pack(score_100, has_blacklist, has_system, has_trigger)

    # ──────────────────────────────────────────────
    # Bucket 계산식
    # ──────────────────────────────────────────────
    @staticmethod
    def _normal_bucket(text: str, non_space_len: int) -> float:
        """0~25: (초성+특수문자) 비율 기반. 0% → 0, 33%+ → 25."""
        if non_space_len <= 0:
            return 0.0
        cho = sum(1 for c in text if _is_standalone_consonant(c))
        spec = sum(1 for c in text if _is_special_char(c))
        ratio = (cho + spec) / non_space_len
        clamped = min(ratio, 0.33)
        return round(clamped / 0.33 * 25.0, 2)

    @staticmethod
    def _caution_bucket(detected_len: int, non_space_len: int) -> float:
        """26~50: 검출단어 길이 비율. 10%↓ → 26, 100% → 50."""
        if non_space_len <= 0:
            return 26.0
        ratio = detected_len / non_space_len
        clamped = max(0.10, min(ratio, 1.0))
        return 26.0 + (clamped - 0.10) / 0.90 * (50.0 - 26.0)

    @staticmethod
    def _warn_bucket(detected_len: int, non_space_len: int) -> float:
        """51~75: 검출단어 길이 비율. 10%↓ → 51, 100% → 75."""
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
