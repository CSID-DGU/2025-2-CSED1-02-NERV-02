"""
Kiwi 형태소 분석기 싱글톤.

앱 lifespan에서 1회 생성되어 FirstPassFilter 와 트렌딩 키워드 엔드포인트가
동일 인스턴스를 공유한다. 1차 필터링의 정규화 책임 대부분을 Kiwi 내장 옵션에
위임하는 방향으로 설계되었다.

핵심 설정:
- global_config.space_tolerance = 1
    "시 발", "시  발" 같은 공백 삽입 우회를 Kiwi 내부에서 병합 후보로 처리.
    한 번 허용되면 공백 개수와 무관하게 동작한다.
- typos='basic_with_continual_and_lengthening'
    모음 늘림(시이이발), 연음, 기본 오타를 편집거리 기반으로 흡수.
- stopwords=Stopwords()
    조사/어미/일부 매우 일반적인 명사를 Kiwi 기본 stopwords 로 제거.
- oov_handling='chr_freq'
    미등록 신조어를 UN 토큰으로 수용하여 트렌드 후보에 반영.
- add_user_word 점수는 기본값(5.0)
    점수를 올리면 동형이의 오탐("숙제 했나 보지" 같은 보조용언 → 명사 오분석)이
    유발되는 것을 실측으로 확인. 경계 유지는 기본 점수만으로 충분하다.

합성명사 인식 규칙 (iter_meaningful_units):
- 인접한 NN*/XR/UN 토큰이 공백 없이 붙어 있으면 하나의 합성명사로 병합.
- NNP 비대칭 규칙: NNP 는 새 run 을 시작할 수 있으나, 앞의 NN* 이
  NNP 로 확장되지는 않는다. 이 규칙을 빼면 "결국김총무" 처럼 선행 NNG 가
  고유명사를 흡수해 트렌드에서 고유명사가 사라진다.
"""
import logging
import threading
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Sequence, cast

from kiwipiepy import Kiwi, Token
from kiwipiepy._wrap import POSTag
from kiwipiepy.utils import Stopwords

logger = logging.getLogger(__name__)

# 합성 대상 태그 (명사/어근/미등록어). 합성 run 은 이 태그들 사이에서만 자란다.
_COMPOUND_TAG_PREFIXES = ("NN", "XR", "UN")

# 필터 매칭 후보로 삼을 의미 형태소 태그.
# - NN*: 일반/고유/의존 명사
# - VV/VA: 동사/형용사 원형 (활용형 자동 환원)
# - XR: 어근
# - SL: 외국어
# - MAG: 일반부사 (신조어 부사 류)
# - UN: 미등록어
_MEANINGFUL_PREFIXES = ("NN", "VV", "VA", "XR", "SL", "MAG", "UN")

# 합성 run 의 최대 길이. 무한 명사 나열을 방지.
_MAX_RUN_TOKENS = 6


@dataclass(frozen=True)
class KiwiUserWord:
    """system_dict_loader 가 돌려주는 등록 엔트리."""
    word: str
    pos: str = "NNG"
    score: float = 5.0


@dataclass(frozen=True)
class MeaningfulUnit:
    """필터 매칭 단위. 단일 의미 토큰 또는 인접 NN* 합성명사."""
    form: str
    start: int
    end: int  # inclusive in raw text
    is_compound: bool


class KiwiEngine:
    def __init__(
        self,
        system_words: Sequence[KiwiUserWord] | None = None,
    ):
        logger.info("[System] KiwiEngine 로딩 중...")
        self._kiwi = Kiwi()
        # space_tolerance 1: 공백 삽입 우회를 병합 후보로 처리
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
                f"[KiwiEngine] 시스템 user_word 등록 완료: {added}/{len(system_words)}"
            )

        logger.info("[System] KiwiEngine 로드 완료 (space_tolerance=1)")

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
        """런타임에 단어들을 user_word 로 등록. 이미 등록된 것은 건너뛴다.

        사용자 사전 갱신이나 트렌드 대표어 동적 등록 시 호출한다.
        점수는 기본값을 유지한다 (오탐 방지).
        """
        added = 0
        with self._lock:
            for w in words:
                if self._register_unlocked(w, pos):
                    added += 1
        return added

    def is_registered(self, word: str) -> bool:
        return word in self._registered

    # ──────────────────────────────────────────────
    # 토큰화
    # ──────────────────────────────────────────────
    def tokenize(self, text: str) -> List[Token]:
        result = self._kiwi.tokenize(
            text,
            normalize_coda=True,
            z_coda=True,
            typos='basic_with_continual_and_lengthening',
            typo_cost_threshold=2.5,
            stopwords=self._stopwords,
            oov_handling='chr_freq',
        )
        return cast(List[Token], result)

    def tokenize_batch(self, texts: Sequence[str]) -> List[List[Token]]:
        """kiwipiepy 네이티브 배치 토큰화 (내부 스레드 풀)."""
        if not texts:
            return []
        text_list = list(texts)
        gen = self._kiwi.tokenize(
            text_list,
            normalize_coda=True,
            z_coda=True,
            typos='basic_with_continual_and_lengthening',
            typo_cost_threshold=2.5,
            stopwords=self._stopwords,
            oov_handling='chr_freq',
        )
        return cast(List[List[Token]], list(gen))

    # ──────────────────────────────────────────────
    # 의미 형태소 단위 추출 (합성명사 병합 포함)
    # ──────────────────────────────────────────────
    @staticmethod
    def iter_meaningful_units(tokens: Sequence[Token]) -> List[MeaningfulUnit]:
        """Kiwi 토큰 리스트를 '필터 매칭 단위' 로 변환.

        - NN*/XR/UN 인접 run 은 하나의 합성명사로 병합
        - VV/VA/SL/MAG 등은 단일 유닛으로 유지
        - NNP 비대칭 규칙 유지 (위 모듈 docstring 참조)
        """
        units: List[MeaningfulUnit] = []
        i = 0
        n = len(tokens)
        while i < n:
            t = tokens[i]
            if not any(t.tag.startswith(p) for p in _MEANINGFUL_PREFIXES):
                i += 1
                continue

            # 합성 대상(NN*/XR/UN) 이 아니면 단일 유닛으로 수집
            if not any(t.tag.startswith(p) for p in _COMPOUND_TAG_PREFIXES):
                units.append(
                    MeaningfulUnit(t.form, t.start, t.start + t.len - 1, False)
                )
                i += 1
                continue

            # 인접 run 확장.
            # NNP 는 앞 run 에 이어지지 않는다 (비대칭 규칙).
            # 자기 자신이 run 을 시작하는 것은 허용되어 뒤따르는 NN*/XR/UN 을 흡수할 수 있다.
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
    # 트렌딩 키워드 추출
    # ──────────────────────────────────────────────
    def extract_trending(
        self,
        texts: Sequence[str],
        tokens_list: Sequence[Sequence[Token]] | None = None,
        min_count: int = 2,
        top_n: int = 20,
    ) -> list[dict]:
        """합성명사 단위로 빈도 상위 키워드를 집계.

        tokens_list 를 함께 넘기면 재토큰화를 건너뛴다 — 필터 파이프라인과
        단일 토큰화를 공유해 "트렌드 + 필터 1-pass" 동작을 가능케 한다.
        """
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

