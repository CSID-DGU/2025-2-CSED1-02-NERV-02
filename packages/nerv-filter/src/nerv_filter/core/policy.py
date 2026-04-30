"""정책 매니저 — scorer 결과 + 보안수준으로 최종 처분 결정."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..models import ModerationAction, SecurityLevel, WordType

logger = logging.getLogger(__name__)


_CAT_BLACKLIST = "BLACKLIST"
_CAT_GENERAL_TRIGGER = "GENERAL_TRIGGER"
_CAT_GENERAL = "GENERAL"


# 매트릭스: [보안모드][검출카테고리] → 액션
_MATRIX: Dict[SecurityLevel, Dict[str, ModerationAction]] = {
    SecurityLevel.LOW: {
        _CAT_BLACKLIST: ModerationAction.PARTIAL_MASK,
        _CAT_GENERAL_TRIGGER: ModerationAction.PARTIAL_MASK,
        _CAT_GENERAL: ModerationAction.REVIEW,
    },
    SecurityLevel.MEDIUM: {
        _CAT_BLACKLIST: ModerationAction.FULL_BLOCK,
        _CAT_GENERAL_TRIGGER: ModerationAction.PARTIAL_MASK,
        _CAT_GENERAL: ModerationAction.PARTIAL_MASK,
    },
    SecurityLevel.HIGH: {
        _CAT_BLACKLIST: ModerationAction.FULL_BLOCK,
        _CAT_GENERAL_TRIGGER: ModerationAction.FULL_BLOCK,
        _CAT_GENERAL: ModerationAction.PARTIAL_MASK,
    },
}


class PolicyManager:
    """검출 결과 + 보안수준 → ModerationAction.

    SDK 공개 API 는 아님. NervFilter 내부에서 사용.
    """

    def __init__(self) -> None:
        logger.debug("[nerv_filter] PolicyManager 로드")

    def decide_action(
        self,
        scorer_result: Dict[str, Any],
        filter_result: Dict[str, Any],
        security_level: SecurityLevel | str,
    ) -> Dict[str, Any]:
        original_text = filter_result.get("original_text", "")
        detected_words = filter_result.get("detected_words", [])
        score = scorer_result.get("score", 0.0)

        if not detected_words:
            return {
                "action": ModerationAction.NORMAL,
                "processed_text": original_text,
                "score": score,
            }

        if scorer_result.get("has_blacklist"):
            category = _CAT_BLACKLIST
        elif scorer_result.get("has_trigger"):
            category = _CAT_GENERAL_TRIGGER
        else:
            category = _CAT_GENERAL

        level = (
            security_level
            if isinstance(security_level, SecurityLevel)
            else SecurityLevel(security_level)
        )
        action = _MATRIX[level][category]

        processed_text = self._render_text(action, original_text, detected_words)

        return {
            "action": action,
            "processed_text": processed_text,
            "score": score,
        }

    def _render_text(
        self,
        action: ModerationAction,
        original_text: str,
        detected_words: List[Dict[str, Any]],
    ) -> str:
        if action == ModerationAction.FULL_BLOCK:
            return ""
        if action == ModerationAction.PARTIAL_MASK:
            return self._star_mask(original_text, detected_words)
        return original_text

    @staticmethod
    def _star_mask(text: str, detected_words: List[Dict[str, Any]]) -> str:
        masked = text
        for item in detected_words:
            word = item.get("word", "")
            if word and item.get("type") != WordType.WHITELIST:
                masked = masked.replace(word, "*" * len(word))
        return masked
