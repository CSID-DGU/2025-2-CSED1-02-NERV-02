"""
한글 자모 분리 및 정규화 모듈

우회 패턴 대응:
- 자모 풀어쓰기: "시발" → "ㅅㅣㅂㅏㄹ"
- 공백 삽입: "시 발" → "시발"
- 쌍자음 치환: "씨발" → "시발"
- 초성 축약: "ㅅㅂ" → 시발의 초성과 매칭
"""

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

# 초성 판별용 set
_CONSONANTS = set(CHOSUNG)


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


def decompose_text(text: str) -> str:
    """텍스트의 모든 완성형 한글을 자모로 분리.
    '시발' → 'ㅅㅣㅂㅏㄹ', 이미 자모인 'ㅅㅂ'는 그대로 유지.
    """
    result = []
    for char in text:
        if _is_hangul_syllable(char):
            result.append(decompose_char(char))
        else:
            result.append(char)
    return ''.join(result)


def extract_chosung(text: str) -> str:
    """텍스트에서 초성만 추출. '시발' → 'ㅅㅂ', 'ㅅㅂ' → 'ㅅㅂ'"""
    result = []
    for char in text:
        if _is_hangul_syllable(char):
            code = ord(char) - _HANGUL_BASE
            cho = code // (21 * 28)
            result.append(CHOSUNG[cho])
        elif char in _CONSONANTS:
            result.append(char)
    return ''.join(result)


def normalize_similar(jamo_text: str) -> str:
    """쌍자음을 단자음으로 정규화. 'ㅆ' → 'ㅅ', 'ㅉ' → 'ㅈ' 등"""
    return ''.join(SIMILAR_CONSONANT.get(c, c) for c in jamo_text)


def is_all_consonants(text: str) -> bool:
    """텍스트가 모두 자음으로만 구성되어 있는지 확인. 'ㅅㅂ' → True"""
    return len(text) > 0 and all(c in _CONSONANTS for c in text)


def levenshtein_distance(s1: str, s2: str, max_dist: int = -1) -> int:
    """Levenshtein 편집 거리 계산. max_dist 설정 시 초과하면 조기 종료."""
    len1, len2 = len(s1), len(s2)
    if abs(len1 - len2) > max_dist > 0:
        return max_dist + 1

    prev = list(range(len2 + 1))
    for i in range(1, len1 + 1):
        curr = [i] + [0] * len2
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        if max_dist > 0 and min(curr) > max_dist:
            return max_dist + 1
        prev = curr
    return prev[len2]


def similarity_ratio(s1: str, s2: str) -> float:
    """두 문자열의 유사도 (0.0 ~ 1.0). 1.0이면 동일."""
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1, s2)
    return 1.0 - (dist / max_len)


def full_normalize(text: str) -> str:
    """전체 정규화 파이프라인: 소문자화 → 공백/특수문자 제거 → 자모 분리 → 유사 자모 정규화"""
    # 1. 소문자화
    text = text.lower()
    # 2. 한글(완성형+낱자), 영문, 숫자만 보존 (공백, 특수문자 제거)
    text = ''.join(
        c for c in text
        if _is_hangul_syllable(c)        # 완성형 한글 (가-힣)
        or '\u3131' <= c <= '\u3163'      # 자모 낱자 (ㄱ-ㅣ)
        or c.isascii() and c.isalnum()    # 영문+숫자
    )
    # 3. 완성형 → 자모 분리
    text = decompose_text(text)
    # 4. 쌍자음 → 단자음 정규화
    text = normalize_similar(text)
    return text
