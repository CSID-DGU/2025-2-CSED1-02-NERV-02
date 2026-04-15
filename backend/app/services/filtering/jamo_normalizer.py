"""
한글 자모 분리 및 정규화 모듈

우회 패턴 대응:
- 자모 풀어쓰기: "시발" → "ㅅㅣㅂㅏㄹ"
- 공백 삽입: "시 발" → "시발"
- 쌍자음 치환: "씨발" → "시발"
- 초성 축약: "ㅅㅂ" → 시발의 초성과 매칭
- 영한 혼합: "si발" → "ㅅㅣㅂㅏㄹ"
- 숫자 치환: "시8" → "시ㅂ"
- 반복 문자: "시이이발" → "시발"
"""

import re

# 한글 유니코드 상수
_HANGUL_BASE = 0xAC00  # '가'
_HANGUL_END = 0xD7A3   # '힣'

# 초성 19자
CHOSUNG = [
    'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
    'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
]

# 중성 21자
JUNGSUNG = [
    'ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ',
    'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ',
]

# 종성 28자 (첫 번째는 종성 없음)
JONGSUNG = [
    '', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ',
    'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ',
    'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
]

# 쌍자음 → 단자음 (유사 발음 정규화)
SIMILAR_CONSONANT = {
    'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ',
}

# 영문 → 한글 자모 매핑 (음가 기반)
_ENG_TO_JAMO = {
    's': 'ㅅ', 'b': 'ㅂ', 'c': 'ㅋ', 'd': 'ㄷ',
    'f': 'ㅍ', 'g': 'ㄱ', 'h': 'ㅎ', 'j': 'ㅈ',
    'k': 'ㅋ', 'l': 'ㄹ', 'm': 'ㅁ', 'n': 'ㄴ',
    'p': 'ㅂ', 'r': 'ㄹ', 't': 'ㅌ', 'v': 'ㅂ',
    'w': 'ㅜ', 'x': 'ㅋ', 'z': 'ㅈ',
    'a': 'ㅏ', 'e': 'ㅔ', 'i': 'ㅣ', 'o': 'ㅗ', 'u': 'ㅜ',
    'y': 'ㅣ',
}

# 숫자 → 한글 자모 매핑 (시각적 유사)
_NUM_TO_JAMO = {
    '0': 'ㅇ', '1': 'ㅣ', '8': 'ㅂ',
}

def _is_hangul_syllable(char: str) -> bool:
    return _HANGUL_BASE <= ord(char) <= _HANGUL_END


def decompose_char(char: str) -> str:
    """완성형 한 글자를 초성+중성+종성으로 분리. 'ㅅㅣ' 같은 낱자는 그대로 반환."""
    code = ord(char) - _HANGUL_BASE
    cho = code // (21 * 28)
    jung = (code % (21 * 28)) // 28
    jong = code % 28
    result = CHOSUNG[cho] + JUNGSUNG[jung]
    if jong > 0:
        result += JONGSUNG[jong]
    return result


def normalize_similar(jamo_text: str) -> str:
    """쌍자음을 단자음으로 정규화. 'ㅆ' → 'ㅅ', 'ㅉ' → 'ㅈ' 등"""
    return ''.join(SIMILAR_CONSONANT.get(c, c) for c in jamo_text)


def normalize_with_map(original_text: str) -> tuple[str, list[int]]:
    """
    텍스트를 자모 단위로 정규화하면서, 원본 인덱스를 추적합니다.
    이 함수가 모든 정규화의 '유일한 핵심 엔진' 역할을 합니다.
    """
    jamo_list = []
    index_map = []
    
    # 한글이 포함되어 있는지 확인 (순수 영문/숫자 오탐 방지용)
    has_hangul = bool(re.search(r'[가-힣ㄱ-ㅣ]', original_text))

    for i, c in enumerate(original_text):
        # 1. 특수문자, 공백 무시
        if not (_is_hangul_syllable(c) or ('\u3131' <= c <= '\u3163') or (c.isascii() and c.isalnum())):
            continue

        c_lower = c.lower()

        # 2. 영문/숫자 -> 자모 변환 (한글이 섞여 있을 때만)
        if has_hangul:
            c_lower = _ENG_TO_JAMO.get(c_lower, c_lower)
            c_lower = _NUM_TO_JAMO.get(c_lower, c_lower)

        # 3. 자모 분리
        if _is_hangul_syllable(c_lower):
            decomposed = decompose_char(c_lower)
        else:
            decomposed = c_lower

        # 4. 쌍자음 정규화 및 연속 문자 압축
        for jamo in decomposed:
            norm_jamo = normalize_similar(jamo)
            
            # 자모 단위 연속 중복 방지 (예: 시이이발 -> ㅅㅣㅂㅏㄹ)
            # 방금 넣은 자모와 똑같은 자모가 들어오려 하면 무시
            if jamo_list and jamo_list[-1] == norm_jamo:
                continue
                
            jamo_list.append(norm_jamo)
            index_map.append(i)

    return "".join(jamo_list), index_map


def full_normalize(text: str) -> str:
    """
    사전 등록용 단일 정규화 함수.
    normalize_with_map의 결과에서 맵핑 데이터는 버리고 텍스트만 반환합니다.
    (두 함수의 로직 불일치 원천 차단)
    """
    normalized_text, _ = normalize_with_map(text)
    return normalized_text