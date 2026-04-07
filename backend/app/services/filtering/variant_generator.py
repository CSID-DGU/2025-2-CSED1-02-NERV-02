"""
치환표 기반 변형 생성기 (넥슨 방식)

사전 빌드 타임에 각 단어의 변형을 미리 생성하여
쿼리 타임에는 정확 매칭만으로 우회 패턴을 잡는다.

"시발" → {"시발", "씨발", "시팔", "씨팔", "시바", "씨바", ...}
모두 자모 정규화 → Aho-Corasick 또는 Set에 등록
"""

from .jamo_normalizer import (
    CHOSUNG, JUNGSUNG, JONGSUNG,
    _HANGUL_BASE, _is_hangul_syllable,
    decompose_char, full_normalize,
)

# ── 음운 치환표 ──
# 실제 우회 패턴에서 관찰되는 치환 관계

# 초성 치환 (발음 유사)
_CHO_SUBS: dict[str, list[str]] = {
    'ㄱ': ['ㄲ'],
    'ㄲ': ['ㄱ'],
    'ㄷ': ['ㄸ'],
    'ㄸ': ['ㄷ'],
    'ㅂ': ['ㅃ', 'ㅍ'],
    'ㅃ': ['ㅂ'],
    'ㅅ': ['ㅆ'],
    'ㅆ': ['ㅅ'],
    'ㅈ': ['ㅉ', 'ㅊ'],
    'ㅉ': ['ㅈ'],
    'ㅊ': ['ㅈ'],
    'ㅍ': ['ㅂ'],
}

# 중성 치환 (발음 유사)
_JUNG_SUBS: dict[str, list[str]] = {
    'ㅏ': ['ㅓ'],
    'ㅓ': ['ㅏ'],
    'ㅗ': ['ㅜ'],
    'ㅜ': ['ㅗ'],
    'ㅐ': ['ㅔ', 'ㅏ'],
    'ㅔ': ['ㅐ', 'ㅓ'],
    'ㅑ': ['ㅏ'],
    'ㅕ': ['ㅓ'],
    'ㅛ': ['ㅗ'],
    'ㅠ': ['ㅜ'],
}


def _compose_syllable(cho: int, jung: int, jong: int) -> str:
    """초성/중성/종성 인덱스로 완성형 한글 조합"""
    return chr(_HANGUL_BASE + (cho * 21 + jung) * 28 + jong)


def _decompose_indices(char: str) -> tuple[int, int, int]:
    """완성형 한글 → (초성idx, 중성idx, 종성idx)"""
    code = ord(char) - _HANGUL_BASE
    cho = code // (21 * 28)
    jung = (code % (21 * 28)) // 28
    jong = code % 28
    return cho, jung, jong


def generate_variants(word: str, max_variants: int = 30) -> set[str]:
    """
    한 단어의 음운 변형을 생성.
    음절 단위로 초성/중성을 치환하고, 종성 탈락도 생성.

    Args:
        word: 원본 단어 (예: "시발")
        max_variants: 최대 변형 수 (조합 폭발 방지)

    Returns:
        정규화된 변형 집합 (자모 형태)
    """
    # 음절 단위로 분리
    syllables = []
    for char in word:
        if _is_hangul_syllable(char):
            syllables.append(char)
        else:
            syllables.append(char)

    if not syllables:
        return {full_normalize(word)}

    # 각 음절의 변형 후보 생성
    syllable_variants: list[list[str]] = []

    for char in syllables:
        if not _is_hangul_syllable(char):
            syllable_variants.append([char])
            continue

        cho_idx, jung_idx, jong_idx = _decompose_indices(char)
        cho_jamo = CHOSUNG[cho_idx]
        jung_jamo = JUNGSUNG[jung_idx]

        variants_for_this: set[str] = {char}

        # 1) 초성 치환
        for alt_cho in _CHO_SUBS.get(cho_jamo, []):
            alt_cho_idx = CHOSUNG.index(alt_cho)
            variants_for_this.add(_compose_syllable(alt_cho_idx, jung_idx, jong_idx))

        # 2) 중성 치환
        for alt_jung in _JUNG_SUBS.get(jung_jamo, []):
            alt_jung_idx = JUNGSUNG.index(alt_jung)
            variants_for_this.add(_compose_syllable(cho_idx, alt_jung_idx, jong_idx))

        # 3) 종성 탈락 (종성이 있을 때)
        if jong_idx > 0:
            variants_for_this.add(_compose_syllable(cho_idx, jung_idx, 0))

        syllable_variants.append(list(variants_for_this))

    # 조합 생성 (폭발 방지: max_variants 제한)
    results: set[str] = set()
    _combine(syllable_variants, 0, [], results, max_variants)

    # 전부 자모 정규화
    return {full_normalize(w) for w in results}


def _combine(
    syllable_variants: list[list[str]],
    idx: int,
    current: list[str],
    results: set[str],
    max_count: int,
) -> None:
    """음절 변형 조합을 재귀적으로 생성"""
    if len(results) >= max_count:
        return
    if idx == len(syllable_variants):
        results.add(''.join(current))
        return
    for variant in syllable_variants[idx]:
        current.append(variant)
        _combine(syllable_variants, idx + 1, current, results, max_count)
        current.pop()


def build_normalized_dictionary(
    system_dict: set[str],
    blacklist: set[str],
    whitelist: set[str],
) -> dict:
    """
    전체 사전을 변형 생성 + 자모 정규화하여 클라이언트 전송용으로 빌드.

    Returns:
        {
            "patterns": {"ㅅㅣㅂㅏㄹ": {"original": "시발", "type": "SYSTEM_KEYWORD"}, ...},
            "whitelist": ["ㅅㅏㄹㅏㅇ", ...],
        }
    """
    patterns: dict[str, dict] = {}

    # 시스템 사전
    for word in system_dict:
        for variant_jamo in generate_variants(word):
            if variant_jamo not in patterns:
                patterns[variant_jamo] = {"original": word, "type": "SYSTEM_KEYWORD"}

    # 유저 블랙리스트 (시스템보다 우선)
    for word in blacklist:
        for variant_jamo in generate_variants(word):
            patterns[variant_jamo] = {"original": word, "type": "USER_BLACKLIST"}

    # 화이트리스트
    whitelist_jamo = [full_normalize(w) for w in whitelist]

    return {
        "patterns": patterns,
        "whitelist": whitelist_jamo,
    }
