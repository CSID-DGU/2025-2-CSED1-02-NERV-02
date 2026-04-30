"""축약 정규화 — 글자 사이 1~2개 숫자/특수문자 제거.

자모 분리는 단어 경계를 깨뜨려 오탐을 만들었던 전례가 있어 사용하지 않는다.
이 모듈은 letter 사이에 의도적으로 끼워넣은 short-noise 만 흡수한다.

규칙 요약:
- 한글/영문을 letter 로 취급
- letter 와 letter 사이에 (공백 아닌) non-letter 가 1~2개 끼면 제거
- 3개 이상 연속이면 보존 (정상 표기일 가능성)
- 공백은 항상 보존 (Kiwi space_tolerance 가 처리)
"""
from __future__ import annotations

import re
from typing import List, Tuple

_LETTER_RE = re.compile(r"[가-힣A-Za-z]")


def is_letter(ch: str) -> bool:
    """한글 음절 또는 영문이면 True."""
    return bool(_LETTER_RE.match(ch))


def compact_normalize(text: str) -> Tuple[str, List[int]]:
    """letter 사이 short-noise 를 제거한 축약 텍스트 + 원문 인덱스 맵 반환.

    Returns:
        ``(normalized_text, index_map)``
        ``index_map[i]`` 는 ``normalized_text[i]`` 가 원문에서 유래한 인덱스.

    Examples:
        >>> compact_normalize("시1발")
        ('시발', [0, 2])
        >>> compact_normalize("시!.발")
        ('시발', [0, 3])
        >>> compact_normalize("시!!!발")    # 3개는 보존
        ('시!!!발', [0, 1, 2, 3, 4])
    """
    out_chars: list[str] = []
    index_map: list[int] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if is_letter(c) or c.isspace():
            out_chars.append(c)
            index_map.append(i)
            i += 1
            continue

        # c 는 숫자/특수문자/기타. 좌측 출력이 letter 일 때만 제거 시도.
        left_is_letter = bool(out_chars) and is_letter(out_chars[-1])
        if left_is_letter:
            j = i
            skip = 0
            while (
                j < n
                and skip < 2
                and not is_letter(text[j])
                and not text[j].isspace()
            ):
                j += 1
                skip += 1
            if j < n and is_letter(text[j]):
                # 1~2 개 중간 문자를 제거하고 건너뛴다
                i = j
                continue

        out_chars.append(c)
        index_map.append(i)
        i += 1
    return "".join(out_chars), index_map
