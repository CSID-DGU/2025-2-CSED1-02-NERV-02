import re
import hashlib
import logging
import ahocorasick

from app.schemas.enums import FilterStatus, WordType
from .jamo_normalizer import full_normalize, extract_chosung
from .variant_generator import generate_variants

logger = logging.getLogger(__name__)


_CacheValue = tuple[
    ahocorasick.Automaton,                            # jamo automaton (변형 포함)
    ahocorasick.Automaton,                            # chosung automaton
]


class FirstPassFilter:
    def __init__(self):
        self._cache: dict[str, _CacheValue] = {}

    _MAX_CACHE_SIZE = 100

    @staticmethod
    def _compute_hash(whitelist: set, blacklist: set, system_dict: set) -> str:
        all_words = sorted(whitelist) + sorted(blacklist) + sorted(system_dict)
        return hashlib.md5("|".join(all_words).encode()).hexdigest()

    @staticmethod
    def _build_cache(
        whitelist: set, blacklist: set, system_dict: set
    ) -> _CacheValue:
        """자모 오토마톤 (변형 포함) + 초성 오토마톤 빌드"""

        # 1) 자모 레벨 오토마톤 — 변형(variant) 포함
        jamo_auto = ahocorasick.Automaton()

        # 화이트리스트 (최우선)
        for w in whitelist:
            jamo_auto.add_word(full_normalize(w), (w, WordType.WHITELIST))

        # 유저 블랙리스트 (변형 포함, 화이트리스트 미등록 패턴만)
        for w in blacklist:
            for variant_jamo in generate_variants(w):
                if variant_jamo not in jamo_auto:
                    jamo_auto.add_word(variant_jamo, (w, WordType.USER_BLACKLIST))

        # 시스템 사전 (변형 포함, 기존 미등록 패턴만)
        for w in system_dict:
            for variant_jamo in generate_variants(w):
                if variant_jamo not in jamo_auto:
                    jamo_auto.add_word(variant_jamo, (w, WordType.SYSTEM_KEYWORD))

        if len(jamo_auto) > 0:
            jamo_auto.make_automaton()

        # 2) 초성 오토마톤 (2글자 이상)
        cho_auto = ahocorasick.Automaton()
        for w in blacklist:
            cho = extract_chosung(w)
            if len(cho) >= 2:
                cho_auto.add_word(cho, (w, WordType.USER_BLACKLIST))
        for w in system_dict:
            cho = extract_chosung(w)
            if len(cho) >= 2:
                cho_auto.add_word(cho, (w, WordType.SYSTEM_KEYWORD))
        if len(cho_auto) > 0:
            cho_auto.make_automaton()

        return jamo_auto, cho_auto

    def execute(self, original_text: str, whitelist: set, blacklist: set, system_dict: set) -> dict:
        # 캐시에서 오토마톤 가져오기 (없으면 빌드)
        cache_key = self._compute_hash(whitelist, blacklist, system_dict)
        if cache_key not in self._cache:
            if len(self._cache) >= self._MAX_CACHE_SIZE:
                self._cache.clear()
            self._cache[cache_key] = self._build_cache(whitelist, blacklist, system_dict)
        jamo_auto, cho_auto = self._cache[cache_key]

        # 텍스트 정규화 (자모 분리 + 유사 자모 정규화)
        normalized = full_normalize(original_text)

        # ── 1단계: 자모 레벨 매칭 ── (source='jamo')
        matches = []
        if len(jamo_auto) > 0:
            for _, (word, wordtype) in jamo_auto.iter(normalized):
                matches.append((word, wordtype, 'jamo'))

        # ── 2단계: 초성 축약 매칭 ── (source='chosung')
        # 원본 텍스트에서 연속 자음 구간을 찾아 초성 오토마톤으로 매칭
        if len(cho_auto) > 0:
            consonant_segments = re.findall(r'[ㄱ-ㅎ]{2,}', original_text)
            for seg in consonant_segments:
                for _, (word, wordtype) in cho_auto.iter(seg):
                    matches.append((word, wordtype, 'chosung'))

        # ── 중복 제거 및 정렬 ──
        seen = set()
        unique_matches = []
        for word, wordtype, source in matches:
            if word not in seen:
                seen.add(word)
                unique_matches.append((word, wordtype, source))

        # 화이트리스트 우선, 긴 단어 우선
        unique_matches.sort(key=lambda x: (0 if x[1] == WordType.WHITELIST else 1, -len(x[0])))

        # ── 결과 생성 ──
        status = FilterStatus.PASSED
        masked_text = normalized
        detected_words = []

        for word, wordtype, source in unique_matches:
            if source == 'jamo':
                norm_word = full_normalize(word)
                if norm_word not in masked_text:
                    continue
                if wordtype == WordType.WHITELIST:
                    masked_text = masked_text.replace(norm_word, "__W__")
                elif wordtype == WordType.USER_BLACKLIST:
                    detected_words.append({'word': word, 'type': WordType.USER_BLACKLIST})
                    masked_text = masked_text.replace(norm_word, "__B__")
                elif wordtype == WordType.SYSTEM_KEYWORD:
                    detected_words.append({'word': word, 'type': WordType.SYSTEM_KEYWORD})
                    masked_text = masked_text.replace(norm_word, "__F__")
            elif source == 'chosung':
                # 초성 매칭: 감지만 기록 (마스킹은 자모 레벨에서 불가)
                if wordtype in (WordType.USER_BLACKLIST, WordType.SYSTEM_KEYWORD):
                    detected_words.append({'word': word, 'type': wordtype})

        if detected_words:
            status = FilterStatus.FILTERED_BY_FIRST_PASS

        return {
            'original_text': original_text,
            'status': status,
            'detected_words': detected_words,
            'masked_text': masked_text,
        }