"""NervFilter — SDK 의 메인 공개 클래스."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable

from ..models import (
    DetectedWord,
    FilterResult,
    ModerationAction,
    ScorerFlags,
    SecurityLevel,
    WordType,
)
from .first_pass import FirstPassFilter
from .kiwi_engine import KiwiEngine
from .policy import PolicyManager
from .scorer import RiskScorer

logger = logging.getLogger(__name__)


class NervFilter:
    """한국어 텍스트 필터링 메인 클래스.

    Args:
        security_level: 정책 강도 (기본 ``MEDIUM``).
        whitelist: 추가 화이트리스트 단어. 동적 갱신 가능.
        blacklist: 추가 블랙리스트 단어. 동적 갱신 가능.
        custom_dict_path: 자체 사전 파일 경로. ``None`` 이면 동봉 사전 사용.
        register_user_words_to_kiwi: 시스템 사전을 Kiwi user_word 로 등록 (기본 True).

    Examples:
        >>> from nerv_filter import NervFilter
        >>> flt = NervFilter()
        >>> result = flt.analyze("이 시발 새끼야")
        >>> result.is_clean
        False
        >>> result.action.value in ("PARTIAL_MASK", "FULL_BLOCK")
        True
    """

    def __init__(
        self,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
        whitelist: Iterable[str] | None = None,
        blacklist: Iterable[str] | None = None,
        custom_dict_path: str | None = None,
        register_user_words_to_kiwi: bool = True,
    ):
        from ..dict.loader import load_default_dict, load_dict

        # 사전 로드
        if custom_dict_path:
            self._system_words, kiwi_user_words = load_dict(custom_dict_path)
        else:
            self._system_words, kiwi_user_words = load_default_dict()

        # 엔진 초기화
        self._kiwi = KiwiEngine(
            system_words=kiwi_user_words if register_user_words_to_kiwi else None
        )
        self._first_pass = FirstPassFilter(self._kiwi)
        self._scorer = RiskScorer()
        self._policy = PolicyManager()

        # 사용자 사전
        self._whitelist: set[str] = set(whitelist or [])
        self._blacklist: set[str] = set(blacklist or [])
        self._security_level = security_level
        self._dict_version = self._compute_version()

    # ──────────────────────────────────────────────
    # 내부 유틸
    # ──────────────────────────────────────────────
    def _compute_version(self) -> str:
        """사전 갱신 시 1차 필터 캐시 무효화 키."""
        return f"v{int(time.time() * 1000000)}"

    def _bump_version(self) -> None:
        self._dict_version = self._compute_version()

    def _to_filter_result(self, text: str, raw: dict) -> FilterResult:
        scorer_result = self._scorer.execute(raw)
        decision = self._policy.decide_action(
            scorer_result=scorer_result,
            filter_result=raw,
            security_level=self._security_level,
        )

        detected = []
        for d in raw.get("detected_words", []):
            wt = d["type"]
            if not isinstance(wt, WordType):
                wt = WordType(wt)
            detected.append(DetectedWord(word=d["word"], word_type=wt))

        return FilterResult(
            original_text=text,
            masked_text=decision["processed_text"],
            action=decision["action"]
            if isinstance(decision["action"], ModerationAction)
            else ModerationAction(decision["action"]),
            score=scorer_result["score"],
            detected_words=detected,
            flags=ScorerFlags(
                has_blacklist=scorer_result["has_blacklist"],
                has_general=scorer_result["has_general"],
                has_trigger=scorer_result["has_trigger"],
            ),
        )

    # ──────────────────────────────────────────────
    # 핵심 분석 API
    # ──────────────────────────────────────────────
    def analyze(self, text: str) -> FilterResult:
        """단일 텍스트 분석."""
        if text is None:
            raise ValueError("text must not be None")
        raw = self._first_pass.execute(
            text,
            self._whitelist,
            self._blacklist,
            self._system_words,
            self._dict_version,
        )
        return self._to_filter_result(text, raw)

    def analyze_batch(self, texts: list[str]) -> list[FilterResult]:
        """배치 분석 — Kiwi 배치 토큰화 활용으로 단일 호출 반복보다 빠름."""
        if not texts:
            return []
        raw_list = self._first_pass.execute_batch(
            texts,
            self._whitelist,
            self._blacklist,
            self._system_words,
            self._dict_version,
        )
        return [
            self._to_filter_result(t, r)
            for t, r in zip(texts, raw_list, strict=False)
        ]

    async def analyze_async(self, text: str) -> FilterResult:
        """비동기 래퍼 — 내부적으로 ``asyncio.to_thread`` 사용."""
        return await asyncio.to_thread(self.analyze, text)

    # ──────────────────────────────────────────────
    # 사전 동적 갱신
    # ──────────────────────────────────────────────
    def add_to_whitelist(self, words: Iterable[str]) -> int:
        """추가, 추가된 개수 반환."""
        before = len(self._whitelist)
        self._whitelist.update(w for w in words if w)
        added = len(self._whitelist) - before
        if added > 0:
            self._bump_version()
        return added

    def add_to_blacklist(self, words: Iterable[str]) -> int:
        before = len(self._blacklist)
        new_words = {w for w in words if w}
        self._blacklist.update(new_words)
        added = len(self._blacklist) - before
        if added > 0:
            self._bump_version()
            # 새로 추가된 단어를 Kiwi user_word 로도 등록
            self._kiwi.register_user_words(new_words - (self._blacklist - new_words))
        return added

    def remove_from_whitelist(self, words: Iterable[str]) -> int:
        before = len(self._whitelist)
        for w in words:
            self._whitelist.discard(w)
        removed = before - len(self._whitelist)
        if removed > 0:
            self._bump_version()
        return removed

    def remove_from_blacklist(self, words: Iterable[str]) -> int:
        before = len(self._blacklist)
        for w in words:
            self._blacklist.discard(w)
        removed = before - len(self._blacklist)
        if removed > 0:
            self._bump_version()
        return removed

    @property
    def whitelist(self) -> set[str]:
        return set(self._whitelist)

    @property
    def blacklist(self) -> set[str]:
        return set(self._blacklist)

    # ──────────────────────────────────────────────
    # 설정
    # ──────────────────────────────────────────────
    @property
    def security_level(self) -> SecurityLevel:
        return self._security_level

    @security_level.setter
    def security_level(self, value: SecurityLevel | str) -> None:
        self._security_level = (
            value if isinstance(value, SecurityLevel) else SecurityLevel(value)
        )

    # ──────────────────────────────────────────────
    # 통계 / 디버깅
    # ──────────────────────────────────────────────
    def get_dictionary_size(self) -> int:
        """현재 시스템 사전 단어 수."""
        return len(self._system_words)
