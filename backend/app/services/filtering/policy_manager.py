import logging
from typing import Dict, Any, List

from app.schemas.enums import ModerationAction, SecurityLevel, WordType

logger = logging.getLogger(__name__)


# 검출 카테고리 (내부용)
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
    def __init__(self):
        logger.info("[System] Policy Manager 로드")

    def decide_action(
        self,
        scorer_result: Dict[str, Any],
        filter_result: Dict[str, Any],
        security_level: SecurityLevel | str,
        ai_soften_enabled: bool = False,
    ) -> Dict[str, Any]:
        original_text = filter_result.get("original_text", "")
        detected_words = filter_result.get("detected_words", [])
        score = scorer_result.get("score", 0.0)

        # 1. 검출 없음 → NORMAL
        if not detected_words:
            return {
                "action": ModerationAction.NORMAL,
                "processed_text": original_text,
                "score": score,
            }

        # 2. 카테고리 결정 (우선순위: 블랙리스트 > 트리거 > 일반)
        # detected_words 가 존재하면 반드시 어딘가에 분류된다 — 플래그가 모두
        # false 로 돌아오는 엣지케이스(신규 WordType 등)는 일반(GENERAL) 로 폴백.
        if scorer_result.get("has_blacklist"):
            category = _CAT_BLACKLIST
        elif scorer_result.get("has_trigger"):
            category = _CAT_GENERAL_TRIGGER
        else:
            category = _CAT_GENERAL

        # 3. 매트릭스 조회
        level = security_level if isinstance(security_level, SecurityLevel) else SecurityLevel(security_level)
        action = _MATRIX[level][category]

        # 4. 액션별 텍스트 가공
        processed_text = self._render_text(action, original_text, detected_words, ai_soften_enabled)

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
        ai_soften_enabled: bool,
    ) -> str:
        if action == ModerationAction.FULL_BLOCK:
            return ""  # 프론트엔드가 "필터링된 댓글입니다" 플레이스홀더 렌더
        if action == ModerationAction.PARTIAL_MASK:
            if ai_soften_enabled:
                return self._ai_soften(original_text, detected_words)
            return self._star_mask(original_text, detected_words)
        # REVIEW, NORMAL은 원문 그대로 (프론트엔드가 검출 단어 라벨로 경고 표시)
        return original_text

    def _star_mask(self, text: str, detected_words: List[Dict[str, Any]]) -> str:
        masked = text
        for item in detected_words:
            word = item.get("word", "")
            if word and item.get("type") != WordType.WHITELIST:
                masked = masked.replace(word, "*" * len(word))
        return masked

    def _ai_soften(self, text: str, detected_words: List[Dict[str, Any]]) -> str:
        # TODO: LLM 순화 연결 (현재는 placeholder — 기본 마스킹으로 폴백)
        return self._star_mask(text, detected_words)
