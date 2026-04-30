"""1차 필터링 — Kiwi 형태소 + Aho-Corasick 다중 채널.

탐지 채널:
  (1) 의미 형태소 단위 직접 매칭
      Kiwi 의 공백 병합(space_tolerance) · typo 교정이 이미 반영된 form 을
      사전과 set 대조한다.
  (2) 원문 Aho-Corasick
      user_word 등록에도 불구하고 Kiwi 가 분리해버린 다중 토큰 매치를 보완.
  (3) 축약 정규화 Aho-Corasick
      "시1발", "시!발" 같은 숫자/특수문자 삽입 우회를 잡는다.

화이트리스트는 별도 Aho-Corasick 으로 수집해 shadow 로 쓰고,
매치 전 구간을 감싸는 화이트리스트 span 과 겹치는 매치는 최종 결과에서 억제한다.

scope 밖 (2차 AI 필터 담당):
- 자모 전면 분해 (ㅅㅣ발)
- 로마자·모양 유사 대체 (s발, ㅅiㅂr)
- 용언 신조어의 미등록 활용형
"""
from __future__ import annotations

import logging
from collections import OrderedDict

import ahocorasick
from kiwipiepy import Token

from ..models import FilterStatus, WordType
from .kiwi_engine import KiwiEngine
from .normalizer import compact_normalize

logger = logging.getLogger(__name__)


_AhoCacheEntry = tuple[ahocorasick.Automaton, ahocorasick.Automaton]


class FirstPassFilter:
    """1차 필터 (Kiwi + Aho-Corasick).

    Args:
        kiwi: 미리 초기화된 KiwiEngine 인스턴스.
    """

    def __init__(self, kiwi: KiwiEngine):
        self._kiwi = kiwi
        self._cache: OrderedDict[str, _AhoCacheEntry] = OrderedDict()
        self._MAX_CACHE_SIZE = 10

    @property
    def kiwi(self) -> KiwiEngine:
        return self._kiwi

    # ──────────────────────────────────────────────
    # Aho-Corasick 캐시
    # ──────────────────────────────────────────────
    @staticmethod
    def _build_aho_cache(
        whitelist: set, blacklist: set, system_dict: set
    ) -> _AhoCacheEntry:
        """블랙+시스템 매치용 / 화이트리스트용 오토마톤 빌드."""
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
        texts: list[str],
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
            for text, tokens in zip(texts, tokens_list, strict=False)
        ]

    # ──────────────────────────────────────────────
    # 단일 텍스트 분석
    # ──────────────────────────────────────────────
    def _analyze_one(
        self,
        original_text: str,
        tokens: list[Token],
        whitelist: set,
        blacklist: set,
        system_dict: set,
        match_auto: ahocorasick.Automaton,
        white_auto: ahocorasick.Automaton,
    ) -> dict:
        whitelist_spans: list[tuple[int, int]] = []
        matches: list[tuple[int, int, str, WordType]] = []

        # POS 마스크: NN*/UN 영역만 매칭 인정 → 동음이의어 오탐 차단
        noun_mask: set[int] = set()
        for tok in tokens:
            if tok.tag.startswith("NN") or tok.tag.startswith("UN"):
                for i in range(tok.start, tok.start + tok.len):
                    noun_mask.add(i)

        def overlaps_noun(s: int, e: int) -> bool:
            return any(i in noun_mask for i in range(s, e + 1))

        # ── (1) 의미 형태소 단위 직접 매칭 ──
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

        # ── (2) 원문 Aho-Corasick ──
        if len(white_auto) > 0:
            for end_idx, wlen in white_auto.iter(original_text):
                whitelist_spans.append((end_idx - wlen + 1, end_idx))
        if len(match_auto) > 0:
            for end_idx, (word, wtype, wlen) in match_auto.iter(original_text):
                s = end_idx - wlen + 1
                if overlaps_noun(s, end_idx):
                    matches.append((s, end_idx, word, wtype))

        # ── (3) 축약 정규화 Aho-Corasick ──
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

        # ── (4) 화이트리스트 shadow ──
        def covered_by_whitelist(s: int, e: int) -> bool:
            return any(ws <= s and e <= we for ws, we in whitelist_spans)

        filtered = [m for m in matches if not covered_by_whitelist(m[0], m[1])]

        # ── (5) 중복 제거 (길이 긴 매치 우선, 블랙 > 시스템) ──
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
