"""Kiwi 형태소 분석기 래퍼.

Kiwi 인스턴스를 보유하고, 사용자 사전 등록 / 토큰화 / 합성명사 병합을 담당한다.

핵심 설정:
- ``global_config.space_tolerance = 1``
    "시 발", "시  발" 같은 공백 삽입 우회를 Kiwi 내부에서 병합 후보로 처리.
- ``typos='basic_with_continual_and_lengthening'``
    모음 늘림(시이이발), 연음, 기본 오타를 편집거리 기반으로 흡수.
- ``stopwords=Stopwords()``
    조사/어미/일부 매우 일반적인 명사를 Kiwi 기본 stopwords 로 제거.
- ``oov_handling='chr_freq'``
    미등록 신조어를 UN 토큰으로 수용.

합성명사 인식 규칙 (``iter_meaningful_units``):
- 인접한 NN*/XR/UN 토큰이 공백 없이 붙어 있으면 하나의 합성명사로 병합.
- NNP 비대칭 규칙: NNP 는 새 run 을 시작할 수 있으나, 앞의 NN* 이
  NNP 로 확장되지는 않는다.
"""
from __future__ import annotations

import logging
import threading
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Sequence, cast

from kiwipiepy import Kiwi, Token
from kiwipiepy._wrap import POSTag
from kiwipiepy.utils import Stopwords

logger = logging.getLogger(__name__)

# 합성 대상 태그 (명사/어근/미등록어).
_COMPOUND_TAG_PREFIXES = ("NN", "XR", "UN")

# 필터 매칭 후보로 삼을 의미 형태소 태그.
_MEANINGFUL_PREFIXES = ("NN", "VV", "VA", "XR", "SL", "MAG", "UN")

# 합성 run 의 최대 길이.
_MAX_RUN_TOKENS = 6


@dataclass(frozen=True)
class KiwiUserWord:
    """Kiwi user_word 등록 엔트리."""

    word: str
    pos: str = "NNG"
    score: float = 5.0


@dataclass(frozen=True)
class MeaningfulUnit:
    """필터 매칭 단위. 단일 의미 토큰 또는 인접 NN* 합성명사."""

    form: str
    start: int
    end: int  # inclusive
    is_compound: bool


class KiwiEngine:
    """Kiwi 형태소 분석기 래퍼.

    Args:
        system_words: 초기화 시 등록할 사용자 사전 단어들.
    """

    def __init__(
        self,
        system_words: Sequence[KiwiUserWord] | None = None,
    ):
        logger.info("[nerv_filter] KiwiEngine 로딩 중...")
        self._kiwi = Kiwi()
        self._kiwi.global_config.space_tolerance = 1
        self._stopwords = Stopwords()
        self._registered: set[str] = set()
        self._lock = threading.Lock()

        if system_words:
            added = 0
            for entry in system_words:
                if self._register_unlocked(entry.word, entry.pos, entry.score):
                    added += 1
            logger.info(
                f"[nerv_filter] KiwiEngine user_word 등록: {added}/{len(system_words)}"
            )

        logger.info("[nerv_filter] KiwiEngine 로드 완료 (space_tolerance=1)")

    @property
    def kiwi(self) -> Kiwi:
        return self._kiwi

    # ──────────────────────────────────────────────
    # 동적 user_word 등록
    # ──────────────────────────────────────────────
    def _register_unlocked(self, word: str, pos: str = "NNG", score: float = 5.0) -> bool:
        if not word or word in self._registered:
            return False
        if self._kiwi.add_user_word(word, cast(POSTag, pos), score):
            self._registered.add(word)
            return True
        return False

    def register_user_words(self, words: Iterable[str], pos: str = "NNG") -> int:
        """런타임에 단어들을 user_word 로 등록. 추가된 개수 반환."""
        added = 0
        with self._lock:
            for w in words:
                if self._register_unlocked(w, pos):
                    added += 1
        if added > 0:
            logger.info(f"[nerv_filter] 동적 user_word {added}건 추가")
        return added

    # ──────────────────────────────────────────────
    # 토큰화
    # ──────────────────────────────────────────────
    def tokenize(self, text: str) -> List[Token]:
        result = self._kiwi.tokenize(
            text,
            normalize_coda=True,
            z_coda=True,
            typos="basic_with_continual_and_lengthening",
            typo_cost_threshold=2.5,
            stopwords=self._stopwords,
            oov_handling="chr_freq",
        )
        return cast(List[Token], result)

    def tokenize_batch(self, texts: Sequence[str]) -> List[List[Token]]:
        """kiwipiepy 네이티브 배치 토큰화."""
        if not texts:
            return []
        text_list = list(texts)
        gen = self._kiwi.tokenize(
            text_list,
            normalize_coda=True,
            z_coda=True,
            typos="basic_with_continual_and_lengthening",
            typo_cost_threshold=2.5,
            stopwords=self._stopwords,
            oov_handling="chr_freq",
        )
        return cast(List[List[Token]], list(gen))

    # ──────────────────────────────────────────────
    # 의미 형태소 단위 추출 (합성명사 병합 포함)
    # ──────────────────────────────────────────────
    @staticmethod
    def iter_meaningful_units(tokens: Sequence[Token]) -> List[MeaningfulUnit]:
        """Kiwi 토큰 리스트를 '필터 매칭 단위' 로 변환."""
        units: List[MeaningfulUnit] = []
        i = 0
        n = len(tokens)
        while i < n:
            t = tokens[i]
            if not any(t.tag.startswith(p) for p in _MEANINGFUL_PREFIXES):
                i += 1
                continue

            if not any(t.tag.startswith(p) for p in _COMPOUND_TAG_PREFIXES):
                units.append(
                    MeaningfulUnit(t.form, t.start, t.start + t.len - 1, False)
                )
                i += 1
                continue

            run_end = i + 1
            while (
                run_end < n
                and run_end - i < _MAX_RUN_TOKENS
                and any(tokens[run_end].tag.startswith(p) for p in _COMPOUND_TAG_PREFIXES)
                and tokens[run_end].start
                == tokens[run_end - 1].start + tokens[run_end - 1].len
                and tokens[run_end].tag != "NNP"
            ):
                run_end += 1

            run_len = run_end - i
            if run_len >= 2:
                form = "".join(tokens[j].form for j in range(i, run_end))
                start = tokens[i].start
                end = tokens[run_end - 1].start + tokens[run_end - 1].len - 1
                units.append(MeaningfulUnit(form, start, end, True))
            else:
                units.append(
                    MeaningfulUnit(t.form, t.start, t.start + t.len - 1, False)
                )
            i = run_end

        return units

    # ──────────────────────────────────────────────
    # 트렌딩 키워드 추출 (옵션)
    # ──────────────────────────────────────────────
    def extract_trending(
        self,
        texts: Sequence[str],
        tokens_list: Sequence[Sequence[Token]] | None = None,
        min_count: int = 2,
        top_n: int = 20,
    ) -> list[dict]:
        """합성명사 단위로 빈도 상위 키워드 집계."""
        if tokens_list is None:
            tokens_list = self.tokenize_batch(list(texts))

        counter: Counter[str] = Counter()
        for tokens in tokens_list:
            for unit in self.iter_meaningful_units(tokens):
                if len(unit.form) >= 2:
                    counter[unit.form] += 1

        return [
            {"word": w, "count": c}
            for w, c in counter.most_common(top_n)
            if c >= min_count
        ]
