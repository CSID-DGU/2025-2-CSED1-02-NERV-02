"""NervFilter — SDK 의 메인 공개 클래스."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable

from ..models import (
    DetectedWord,
    FilterResult,
    FilterStatus,
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
        second_pass=None,
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

        # 2차 필터 (선택). SecondPassConfig 를 주면 탐지기 생성.
        # 로드 실패해도 detector.is_active=False 라 1차만으로 동작.
        self._second_pass = None
        if second_pass is not None:
            try:
                from ..second_pass import SecondPassConfig, SecondPassDetector
                if isinstance(second_pass, SecondPassConfig):
                    self._second_pass = SecondPassDetector(second_pass)
                else:
                    # 이미 Detector 인스턴스를 받은 경우
                    self._second_pass = second_pass
            except Exception as e:
                logger.error("[nerv_filter] 2차 필터 초기화 실패 — 1차만 사용: %s", e)
                self._second_pass = None

    # ──────────────────────────────────────────────
    # 내부 유틸
    # ──────────────────────────────────────────────
    def _compute_version(self) -> str:
        """사전 갱신 시 1차 필터 캐시 무효화 키."""
        return f"v{int(time.time() * 1000000)}"

    def _bump_version(self) -> None:
        self._dict_version = self._compute_version()

    def _apply_second_pass(self, text: str, raw: dict, use_second_pass: bool = True) -> dict:
        """1차 결과에 2차(AI) 점수를 조건부로 합친다.

        - ``use_second_pass=False`` → 2차 건너뜀 (per-request on/off)
        - 2차 비활성/로드실패 → raw 그대로 (1차만)
        - 1차에서 blacklist/trigger 확실 → 2차 스킵 (성능)
        - AI 점수: raw['second_pass_scores'] = {module: score} 형태로 저장.
          threshold 통과 모듈이 있고 사전 검출이 없다면 detected_words 에 AI_BASIC 추가 +
          위치 불명이라 문장 전체 마스킹.
        - 어떤 단계든 예외는 detector 내부에서 흡수 → 항상 1차 결과 보존.
        """
        if not use_second_pass:
            return raw
        if self._second_pass is None or not self._second_pass.is_active:
            return raw

        pre = self._scorer.execute(raw)
        if pre.get("has_blacklist") or pre.get("has_trigger"):
            return raw  # 1차에서 이미 확실 → 2차 불필요

        scores = self._second_pass.predict(text)
        if not scores:
            return raw

        threshold = getattr(self._second_pass.config, "threshold", 0.8)
        hits = [name for name, s in scores.items() if s >= threshold]

        raw = dict(raw)
        raw["second_pass_scores"] = scores
        if hits and not raw.get("detected_words"):
            # AI 만 트리거되고 1차 검출 없는 경우 — 카테고리를 detected_words 에 기록 + 전체 마스킹
            raw["detected_words"] = [
                {"word": cat, "type": WordType.AI_BASIC} for cat in hits
            ]
            raw["status"] = FilterStatus.FILTERED_BY_SECOND_PASS
            raw["masked_text"] = "".join("*" if not c.isspace() else c for c in text)
        return raw

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
    def _resolve_lists(
        self,
        whitelist: Iterable[str] | None,
        blacklist: Iterable[str] | None,
    ) -> tuple[set[str], set[str], str]:
        """요청별 whitelist/blacklist override 해석.

        둘 다 None 이면 인스턴스 기본값 + 기존 dict_version 사용 (캐시 효율).
        하나라도 주어지면 내용 해시로 per-request 캐시 키를 만든다.
        """
        if whitelist is None and blacklist is None:
            return self._whitelist, self._blacklist, self._dict_version
        wl = set(whitelist) if whitelist is not None else self._whitelist
        bl = set(blacklist) if blacklist is not None else self._blacklist
        import hashlib

        h = hashlib.md5()
        h.update(repr(sorted(wl)).encode("utf-8"))
        h.update(b"|")
        h.update(repr(sorted(bl)).encode("utf-8"))
        return wl, bl, f"req-{h.hexdigest()[:16]}"

    def analyze(
        self,
        text: str,
        whitelist: Iterable[str] | None = None,
        blacklist: Iterable[str] | None = None,
        use_second_pass: bool = True,
    ) -> FilterResult:
        """단일 텍스트 분석.

        Args:
            text: 분석할 텍스트.
            whitelist: 이 호출에만 적용할 화이트리스트 override.
            blacklist: 이 호출에만 적용할 블랙리스트 override.
            use_second_pass: 2차(AI) 필터 사용 여부. ``False`` 면 1차만으로 분석.
                인스턴스 자체에 2차가 비활성/미설정이면 이 값 무관하게 1차만.
        """
        if text is None:
            raise ValueError("text must not be None")
        wl, bl, version = self._resolve_lists(whitelist, blacklist)
        raw = self._first_pass.execute(text, wl, bl, self._system_words, version)
        raw = self._apply_second_pass(text, raw, use_second_pass=use_second_pass)
        return self._to_filter_result(text, raw)

    def analyze_batch(
        self,
        texts: list[str],
        whitelist: Iterable[str] | None = None,
        blacklist: Iterable[str] | None = None,
        use_second_pass: bool = True,
    ) -> list[FilterResult]:
        """배치 분석 — Kiwi 배치 토큰화 활용으로 단일 호출 반복보다 빠름."""
        if not texts:
            return []
        wl, bl, version = self._resolve_lists(whitelist, blacklist)
        raw_list = self._first_pass.execute_batch(
            texts, wl, bl, self._system_words, version
        )
        return [
            self._to_filter_result(t, self._apply_second_pass(t, r, use_second_pass=use_second_pass))
            for t, r in zip(texts, raw_list, strict=False)
        ]

    async def analyze_async(self, text: str, use_second_pass: bool = True) -> FilterResult:
        """비동기 래퍼 — 내부적으로 ``asyncio.to_thread`` 사용."""
        return await asyncio.to_thread(self.analyze, text, None, None, use_second_pass)

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
