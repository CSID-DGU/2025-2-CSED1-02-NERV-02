"""
1차 필터링 (단일 단계).

정규화 책임은 대부분 KiwiEngine 이 가져간다. 본 모듈은 Kiwi 가 돌려준 의미
형태소 단위와 "글자 사이 숫자/특수문자 1~2개 제거" 축약 정규화 문자열 두
채널을 통합 아호코라식으로 매칭해 탐지 결과를 모은다.

탐지 채널:
  (1) 의미 형태소 단위 직접 매칭
      Kiwi 의 공백 병합(space_tolerance)·typo 교정이 이미 반영된 form 을
      사전과 set 대조한다. "시 발" → token.form="시발" 같은 케이스를 잡는다.
  (2) 원문 아호코라식
      user_word 등록에도 불구하고 Kiwi 가 분리해버린 다중 토큰 매치를 보완.
  (3) 축약 정규화 아호코라식
      "시1발", "시!발" 같은 숫자/특수문자 삽입 우회를 잡는다. 정규화 공간의
      인덱스 맵으로 원문 좌표를 환원한다.

화이트리스트는 별도 아호코라식으로 수집해 shadow 로 쓰고, 매치 전 구간을
감싸는 화이트리스트 span 과 겹치는 블랙/시스템 매치는 최종 결과에서 억제한다.

scope 밖 (2차 AI 필터 담당):
  - 자모 전면 분해 (ㅅㅣ발)
  - 로마자·모양 유사 대체 (s발, ㅅiㅂr)
  - 용언 신조어의 미등록 활용형
"""
import logging
import re
from collections import OrderedDict
from typing import List, Tuple

import ahocorasick
from kiwipiepy import Token

from app.schemas.enums import FilterStatus, WordType
from .kiwi_engine import KiwiEngine

logger = logging.getLogger(__name__)


_LETTER_RE = re.compile(r'[\uac00-\ud7a3A-Za-z]')


def _is_letter(ch: str) -> bool:
    return bool(_LETTER_RE.match(ch))


def compact_normalize(text: str) -> Tuple[str, List[int]]:
    """글자 사이에 낀 숫자·특수문자 1~2개를 제거한 축약 문자열과 원문 인덱스 맵.

    규칙:
      - 한글/영문 글자를 "letter" 로 취급
      - letter 뒤에 letter 가 아닌 (공백도 아닌) 문자가 1~2개 연속으로 오고
        그 다음 letter 가 이어지면 그 사이 문자를 제거
      - 3개 이상 연속은 제거하지 않음 (의도적 삽입보다 정상 표기 가능성)
      - 공백은 항상 유지 — Kiwi 의 space_tolerance 가 공백 처리를 담당하므로
        여기서 중복 처리하면 문맥 붕괴 위험이 있다

    반환:
      (normalized_text, index_map)
      index_map[i] = normalized_text[i] 가 원문에서 유래한 문자 인덱스
    """
    out_chars: list[str] = []
    index_map: list[int] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if _is_letter(c) or c.isspace():
            out_chars.append(c)
            index_map.append(i)
            i += 1
            continue

        # c 는 숫자/특수문자/기타. 앞쪽 출력이 letter 인 경우 제거 시도.
        left_is_letter = bool(out_chars) and _is_letter(out_chars[-1])
        if left_is_letter:
            j = i
            skip = 0
            while (
                j < n
                and skip < 2
                and not _is_letter(text[j])
                and not text[j].isspace()
            ):
                j += 1
                skip += 1
            if j < n and _is_letter(text[j]):
                # 1~2 개 중간 문자를 제거하고 건너뛴다
                i = j
                continue

        out_chars.append(c)
        index_map.append(i)
        i += 1
    return "".join(out_chars), index_map


_AhoCacheEntry = Tuple[ahocorasick.Automaton, ahocorasick.Automaton]


class FirstPassFilter:
    def __init__(self, kiwi: KiwiEngine):
        self._kiwi = kiwi
        self._cache: "OrderedDict[str, _AhoCacheEntry]" = OrderedDict()
        self._MAX_CACHE_SIZE = 10

    @property
    def kiwi(self) -> KiwiEngine:
        return self._kiwi

    # ──────────────────────────────────────────────
    # 아호코라식 캐시
    # ──────────────────────────────────────────────
    @staticmethod
    def _build_aho_cache(
        whitelist: set, blacklist: set, system_dict: set
    ) -> _AhoCacheEntry:
        """블랙+시스템 을 단일 매치용 오토마톤에, 화이트리스트를 별도 오토마톤에 빌드."""
        match_auto = ahocorasick.Automaton()
        added: set[str] = set()
        for w in blacklist:
            if w and w not in added:
                match_auto.add_word(w, (w, WordType.USER_BLACKLIST, len(w)))
                added.add(w)
        for w in system_dict:
            if w and w not in added:
                match_auto.add_word(w, (w, WordType.SYSTEM_KEYWORD, len(w)))
                added.add(w)
        if len(match_auto) > 0:
            match_auto.make_automaton()

        white_auto = ahocorasick.Automaton()
        for w in whitelist:
            if w and w not in white_auto:
                white_auto.add_word(w, len(w))
        if len(white_auto) > 0:
            white_auto.make_automaton()

        return match_auto, white_auto

    def _get_aho_cache(
        self, whitelist: set, blacklist: set, system_dict: set, dict_version: str
    ) -> _AhoCacheEntry:
        if dict_version in self._cache:
            self._cache.move_to_end(dict_version)
            return self._cache[dict_version]
        if len(self._cache) >= self._MAX_CACHE_SIZE:
            self._cache.popitem(last=False)
        entry = self._build_aho_cache(whitelist, blacklist, system_dict)
        self._cache[dict_version] = entry
        return entry

    # ──────────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────────
    def execute(
        self,
        original_text: str,
        whitelist: set,
        blacklist: set,
        system_dict: set,
        dict_version: str = "latest",
    ) -> dict:
        tokens = self._kiwi.tokenize(original_text)
        match_auto, white_auto = self._get_aho_cache(
            whitelist, blacklist, system_dict, dict_version
        )
        return self._analyze_one(
            original_text,
            tokens,
            whitelist,
            blacklist,
            system_dict,
            match_auto,
            white_auto,
        )

    def execute_batch(
        self,
        texts: List[str],
        whitelist: set,
        blacklist: set,
        system_dict: set,
        dict_version: str = "latest",
    ) -> list[dict]:
        if not texts:
            return []
        tokens_list = self._kiwi.tokenize_batch(texts)
        match_auto, white_auto = self._get_aho_cache(
            whitelist, blacklist, system_dict, dict_version
        )
        return [
            self._analyze_one(
                text,
                tokens,
                whitelist,
                blacklist,
                system_dict,
                match_auto,
                white_auto,
            )
            for text, tokens in zip(texts, tokens_list)
        ]

    # ──────────────────────────────────────────────
    # 단일 텍스트 분석
    # ──────────────────────────────────────────────
    def _analyze_one(
        self,
        original_text: str,
        tokens: List[Token],
        whitelist: set,
        blacklist: set,
        system_dict: set,
        match_auto: ahocorasick.Automaton,
        white_auto: ahocorasick.Automaton,
    ) -> dict:
        whitelist_spans: list[tuple[int, int]] = []
        matches: list[tuple[int, int, str, WordType]] = []

        # 명사성 토큰(NN*/UN) 이 차지하는 원문 char 위치 set.
        # Channel 2/3 의 바이트 매치가 POS 컨텍스트를 뒤덮지 않도록,
        # 이 영역과 겹치는 매치만 인정한다. (예: "숙제 했나 보지" 에서
        # "보지" 구간은 VX+EF 라 noun_mask 에 없음 → 오탐 차단)
        noun_mask: set[int] = set()
        for tok in tokens:
            if tok.tag.startswith("NN") or tok.tag.startswith("UN"):
                for i in range(tok.start, tok.start + tok.len):
                    noun_mask.add(i)

        def overlaps_noun(s: int, e: int) -> bool:
            return any(i in noun_mask for i in range(s, e + 1))

        # ── (1) 의미 형태소 단위 직접 매칭 ──
        # 합성 유닛 + 개별 토큰 양쪽을 본다. 합성 병합이 단일 토큰 매치를
        # 집어삼키는 경우 ("시 발년아" → Kiwi 가 "시발"+"년" 으로 분리한 뒤
        # 합성 유닛에서 "시발년" 으로 묶이는) 를 커버한다.
        for unit in KiwiEngine.iter_meaningful_units(tokens):
            form = unit.form
            span = (unit.start, unit.end)
            if form in whitelist:
                whitelist_spans.append(span)
                continue
            if form in blacklist:
                matches.append((span[0], span[1], form, WordType.USER_BLACKLIST))
            elif form in system_dict:
                matches.append((span[0], span[1], form, WordType.SYSTEM_KEYWORD))

        for tok in tokens:
            form = tok.form
            span = (tok.start, tok.start + tok.len - 1)
            if form in whitelist:
                whitelist_spans.append(span)
                continue
            if form in blacklist:
                matches.append((span[0], span[1], form, WordType.USER_BLACKLIST))
            elif form in system_dict:
                matches.append((span[0], span[1], form, WordType.SYSTEM_KEYWORD))

        # ── (2) 원문 아호코라식 ──
        # 화이트리스트는 그대로 수집 (shadow 목적상 POS 필터 불필요).
        # 매치는 noun_mask 와 겹칠 때만 인정 → POS 오탐 차단.
        if len(white_auto) > 0:
            for end_idx, wlen in white_auto.iter(original_text):
                whitelist_spans.append((end_idx - wlen + 1, end_idx))
        if len(match_auto) > 0:
            for end_idx, (word, wtype, wlen) in match_auto.iter(original_text):
                s = end_idx - wlen + 1
                if overlaps_noun(s, end_idx):
                    matches.append((s, end_idx, word, wtype))

        # ── (3) 축약 정규화 아호코라식 ──
        norm_text, index_map = compact_normalize(original_text)
        if norm_text and norm_text != original_text:
            if len(white_auto) > 0:
                for end_idx, wlen in white_auto.iter(norm_text):
                    start_idx = end_idx - wlen + 1
                    if 0 <= start_idx and end_idx < len(index_map):
                        whitelist_spans.append(
                            (index_map[start_idx], index_map[end_idx])
                        )
            if len(match_auto) > 0:
                for end_idx, (word, wtype, wlen) in match_auto.iter(norm_text):
                    start_idx = end_idx - wlen + 1
                    if 0 <= start_idx and end_idx < len(index_map):
                        orig_s = index_map[start_idx]
                        orig_e = index_map[end_idx]
                        if overlaps_noun(orig_s, orig_e):
                            matches.append((orig_s, orig_e, word, wtype))

        # ── (4) 화이트리스트 shadow: 감싸는 span 내부 매치 억제 ──
        def covered_by_whitelist(s: int, e: int) -> bool:
            return any(ws <= s and e <= we for ws, we in whitelist_spans)

        filtered = [m for m in matches if not covered_by_whitelist(m[0], m[1])]

        # ── (5) 중복 제거 (길이 긴 매치 우선, 블랙 > 시스템) ──
        # 정렬 키: start 오름 → 길이 내림 → 블랙 우선.
        # 긴 매치를 먼저 accept 한 뒤, 그 안에 완전히 포함되는 짧은 매치는 버린다
        # ("쥐똥고추" 가 잡히면 "고추" 는 의미 없음, "시발년" 유닛과 "시발" 토큰이
        # 공존하면 긴 쪽만 남긴다).
        filtered.sort(
            key=lambda m: (
                m[0],
                -(m[1] - m[0]),
                0 if m[3] == WordType.USER_BLACKLIST else 1,
            )
        )
        seen_keys: set[tuple[int, int, str]] = set()
        final_matches: list[tuple[int, int, str, WordType]] = []
        detected_words: list[dict] = []
        for s, e, word, wtype in filtered:
            key = (s, e, word)
            if key in seen_keys:
                continue
            contained = any(
                fs <= s and e <= fe and (fs, fe) != (s, e)
                for fs, fe, _, _ in final_matches
            )
            if contained:
                continue
            seen_keys.add(key)
            final_matches.append((s, e, word, wtype))
            detected_words.append({"word": word, "type": wtype})

        # ── (6) 마스킹 렌더 ──
        if final_matches:
            masked_chars = list(original_text)
            for s, e, _, _ in final_matches:
                for i in range(s, e + 1):
                    if 0 <= i < len(masked_chars):
                        masked_chars[i] = "*"
            masked_text = "".join(masked_chars)
            status = FilterStatus.FILTERED_BY_FIRST_PASS
        else:
            masked_text = original_text
            status = FilterStatus.PASSED

        return {
            "original_text": original_text,
            "status": status,
            "detected_words": detected_words,
            "masked_text": masked_text,
        }