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

_AI_MASK_THRESHOLDS: dict[str, float] = {
    "basic": 0.15,
    "sexual": 0.20,
    "criticism": 0.40,
    "politics": 0.20,
    "family": 1.50,
}

_AI_DETECTION_THRESHOLDS: dict[str, float] = {
    "spam": 0.70,
    "pii": 0.80,
}

_AI_FULL_BLOCK_MODULES = {"spam", "pii"}
_AI_BLOCK_MESSAGE = "[안전 정책에 따라 차단된 메시지]"
_LAUGHTER_CHARS = {"ㅋ", "ㅎ"}
_SECOND_PASS_TRIGGER_MAX_KEYWORD_RATIO = 0.30

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
        - 1차 검출 단어 길이 비율이 0.30 이상이면 1차 결과만 사용.
        - 1차 검출 단어 길이 비율이 0.30 미만이면 2차 실행 후 2차 마스킹만 사용.
        - 원문 텍스트로 2차 실행.
        - 2차가 정상으로 판단하면 1차 결과도 정상으로 되돌림.
        - AI 점수: raw['second_pass_scores'] = {module: score} 형태로 저장.
        - 어떤 단계든 예외는 detector 내부에서 흡수 → 항상 1차 결과 보존.
        """
        if not use_second_pass:
            return raw
        if self._second_pass is None or not self._second_pass.is_active:
            return raw

        keyword_ratio = self._first_pass_keyword_ratio(text, raw)
        if keyword_ratio >= _SECOND_PASS_TRIGGER_MAX_KEYWORD_RATIO:
            return raw

        second_text = text
        if not second_text.strip():
            return raw

        details = {}
        if hasattr(self._second_pass, "predict_with_details"):
            details = self._second_pass.predict_with_details(second_text)
        scores = {
            name: float(info.get("score", 0.0))
            for name, info in details.items()
        } if details else self._second_pass.predict(second_text)
        if not scores:
            return raw

        threshold = getattr(self._second_pass.config, "threshold", 0.8)
        hits = [
            name
            for name, score in scores.items()
            if score >= _AI_DETECTION_THRESHOLDS.get(name, threshold)
        ]
        if (
            "basic" in hits
            and {"criticism", "sexual"}.intersection(hits)
            and not _AI_FULL_BLOCK_MODULES.intersection(hits)
        ):
            # basic 과 criticism/sexual 이 같이 잡히면 criticism/sexual 만 제거하고,
            # basic 및 다른 모듈은 유지한다.
            hits = [name for name in hits if name not in {"criticism", "sexual"}]
            scores = {
                name: score
                for name, score in scores.items()
                if name not in {"criticism", "sexual"}
            }
            if details:
                details = {
                    name: info
                    for name, info in details.items()
                    if name not in {"criticism", "sexual"}
                }

        if "criticism" in hits and "sexual" in hits:
            winner = (
                "criticism"
                if scores.get("criticism", 0.0) >= scores.get("sexual", 0.0)
                else "sexual"
            )
            loser = "sexual" if winner == "criticism" else "criticism"
            hits = [name for name in hits if name != loser]
            scores = {name: score for name, score in scores.items() if name != loser}
            if details:
                details = {name: info for name, info in details.items() if name != loser}

        if "criticism" in hits and len(hits) > 1:
            # criticism 은 단독 검출일 때만 적용. 다른 모듈과 동시 검출되면 노이즈로 본다.
            hits = [name for name in hits if name != "criticism"]
            scores = {name: score for name, score in scores.items() if name != "criticism"}
            if details:
                details = {name: info for name, info in details.items() if name != "criticism"}

        if "sexual" in hits and len(hits) > 1:
            # sexual 은 criticism 과의 단독 경합을 제외하면, 다른 모듈과 동시 검출 시 제거한다.
            hits = [name for name in hits if name != "sexual"]
            scores = {name: score for name, score in scores.items() if name != "sexual"}
            if details:
                details = {name: info for name, info in details.items() if name != "sexual"}

        if "politics" in hits and "family" in hits:
            winner = (
                "politics"
                if scores.get("politics", 0.0) >= scores.get("family", 0.0)
                else "family"
            )
            loser = "family" if winner == "politics" else "politics"
            hits = [name for name in hits if name != loser]
            scores = {name: score for name, score in scores.items() if name != loser}
            if details:
                details = {name: info for name, info in details.items() if name != loser}

        raw = dict(raw)
        raw["second_pass_scores"] = scores
        if details:
            raw["second_pass_details"] = details
        if not hits:
            return self._reset_to_clean(raw, text)

        if hits:
            detected = []
            detected_keys = set()
            for cat in hits:
                key = (cat, WordType.AI_BASIC)
                if key not in detected_keys:
                    detected.append({"word": cat, "type": WordType.AI_BASIC})
                    detected_keys.add(key)
            raw["detected_words"] = detected
            raw["status"] = FilterStatus.FILTERED_BY_SECOND_PASS
            raw["ai_modules"] = hits
            if any(cat in _AI_FULL_BLOCK_MODULES for cat in hits):
                raw["masked_text"] = _AI_BLOCK_MESSAGE
                raw["action_override"] = ModerationAction.FULL_BLOCK
            else:
                raw["masked_text"] = self._render_second_pass_mask(second_text, hits, details)
        return raw

    @staticmethod
    def _first_pass_keyword_ratio(text: str, raw: dict) -> float:
        """1차 마스킹 길이 / 원문 공백 제외 길이."""
        non_space_len = sum(1 for ch in text if not ch.isspace())
        if non_space_len <= 0:
            return 0.0
        masked_text = raw.get("masked_text") or ""
        masked_len = sum(1 for ch in masked_text if ch == "*")
        return masked_len / non_space_len

    @staticmethod
    def _reset_to_clean(raw: dict, text: str) -> dict:
        """2차가 정상으로 본 문장은 1차 검출도 정상 결과로 되돌린다."""
        clean = dict(raw)
        clean["status"] = FilterStatus.PASSED
        clean["detected_words"] = []
        clean["masked_text"] = text
        clean.pop("ai_modules", None)
        clean.pop("action_override", None)
        return clean

    @staticmethod
    def _is_laughter_span(text: str) -> bool:
        compact = "".join(ch for ch in text if not ch.isspace())
        return bool(compact) and all(ch in _LAUGHTER_CHARS for ch in compact)

    @classmethod
    def _render_second_pass_mask(cls, text: str, hits: list[str], details: dict) -> str:
        """attention * max(logit, 0) evidence 로 2차 부분 마스킹."""
        if not details:
            return "".join("*" if not c.isspace() else c for c in text)

        spans: list[tuple[int, int]] = []
        for module_name in hits:
            mask_threshold = _AI_MASK_THRESHOLDS.get(module_name)
            if mask_threshold is None:
                continue
            module_details = details.get(module_name) or {}
            spans.extend(
                cls._evidence_spans(
                    text,
                    module_details.get("token_evidence") or [],
                    mask_threshold,
                )
            )

        if not spans:
            return text

        chars = list(text)
        for start, end in spans:
            for idx in range(start, end):
                if 0 <= idx < len(chars) and not chars[idx].isspace():
                    chars[idx] = "*"
        return "".join(chars)

    @classmethod
    def _merge_second_pass_mask(
        cls,
        first_masked_text: str,
        second_text: str,
        hits: list[str],
        details: dict,
    ) -> str:
        """2차 evidence span 을 1차 마스킹 결과와 병합.

        2차 토큰 span 안에 1차 마스킹(``*``)이 이미 포함되어 있으면,
        그 토큰은 1차 필터 결과만 유지하고 2차 마스킹을 추가하지 않는다.
        """
        if not details:
            return first_masked_text

        chars = list(first_masked_text)
        for module_name in hits:
            mask_threshold = _AI_MASK_THRESHOLDS.get(module_name)
            if mask_threshold is None:
                continue
            module_details = details.get(module_name) or {}
            spans = cls._evidence_spans(
                second_text,
                module_details.get("token_evidence") or [],
                mask_threshold,
                first_masked_text=first_masked_text,
            )
            for start, end in spans:
                for idx in range(start, end):
                    if 0 <= idx < len(chars) and not chars[idx].isspace():
                        chars[idx] = "*"
        return "".join(chars)

    @classmethod
    def _evidence_spans(
        cls,
        text: str,
        token_evidence: list[dict],
        threshold: float,
        first_masked_text: str | None = None,
    ) -> list[tuple[int, int]]:
        """WordPiece evidence 병합 후 threshold 이상 span 반환.

        병합 점수는 max(max_subtoken, sum / n^0.25).
        """
        groups: list[list[dict]] = []
        current: list[dict] = []
        previous_end: int | None = None

        for item in sorted(token_evidence, key=lambda x: (int(x["start"]), int(x["end"]))):
            start = int(item["start"])
            end = int(item["end"])
            if start >= end:
                continue
            token = str(item.get("token", ""))
            is_continuation = token.startswith("##")
            if current and (is_continuation or start <= (previous_end or start)):
                current.append(item)
            else:
                if current:
                    groups.append(current)
                current = [item]
            previous_end = max(previous_end or end, end)

        if current:
            groups.append(current)

        spans: list[tuple[int, int]] = []
        for group in groups:
            start = min(int(item["start"]) for item in group)
            end = max(int(item["end"]) for item in group)
            if cls._is_laughter_span(text[start:end]):
                continue
            if first_masked_text is not None and "*" in first_masked_text[start:end]:
                continue
            evidences = [float(item.get("evidence", 0.0)) for item in group]
            n = max(len(evidences), 1)
            merged = max(max(evidences), sum(evidences) / (n ** 0.25))
            if merged >= threshold:
                spans.append((start, end))
        return spans

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
