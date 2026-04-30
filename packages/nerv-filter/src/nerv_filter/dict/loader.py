"""사전 로더 — 패키지 동봉 default_dic.json 또는 사용자 지정 파일 로드.

dic.json 스키마:
    {
      "category": {
        "root_word": {"pos": "NNG|VV|...", "variants": [...]}
      }
    }
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from importlib.resources import files
from pathlib import Path

from ..core.kiwi_engine import KiwiUserWord
from ..exceptions import DictionaryError

logger = logging.getLogger(__name__)


_DEFAULT_POS = "NNG"
_VARIANT_POS = "NNG"
_ROOT_SCORE = 5.0
_VARIANT_SCORE = 3.0


def get_default_dict_path() -> Path:
    """패키지 동봉 default_dic.json 경로 반환."""
    return Path(str(files("nerv_filter.dict") / "default_dic.json"))


def load_default_dict() -> tuple[set[str], list[KiwiUserWord]]:
    """패키지 동봉 사전 로드."""
    return load_dict(get_default_dict_path())


def load_dict(path: str | Path) -> tuple[set[str], list[KiwiUserWord]]:
    """사용자 지정 사전 로드.

    Returns:
        ``(flat_word_set, kiwi_user_words)``

    Raises:
        DictionaryError: 파일이 없거나 JSON 파싱 실패 시.
    """
    p = Path(path)
    if not p.exists():
        raise DictionaryError(f"Dictionary file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DictionaryError(f"Failed to parse {p}: {e}") from e

    return _build_word_set(data)


def _build_word_set(data: dict) -> tuple[set[str], list[KiwiUserWord]]:
    words: set[str] = set()
    user_words: list[KiwiUserWord] = []

    for category, roots in data.items():
        if category.startswith("_"):
            continue
        if not isinstance(roots, dict):
            continue
        for root, payload in roots.items():
            pos, variants = _parse_entry(payload)
            words.add(root)
            user_words.append(KiwiUserWord(word=root, pos=pos, score=_ROOT_SCORE))
            for v in variants:
                if not v:
                    continue
                words.add(v)
                user_words.append(
                    KiwiUserWord(word=v, pos=_VARIANT_POS, score=_VARIANT_SCORE)
                )

    logger.info(
        f"[nerv_filter] 사전 로드 완료: {len(words)}개 단어, user_word {len(user_words)}건"
    )
    return words, user_words


def _parse_entry(payload) -> tuple[str, Iterable[str]]:
    """엔트리 포맷 정규화. dict 또는 list 모두 허용."""
    if isinstance(payload, dict):
        pos = payload.get("pos", _DEFAULT_POS)
        variants = payload.get("variants", [])
        return pos, list(variants)
    if isinstance(payload, list):
        return _DEFAULT_POS, list(payload)
    return _DEFAULT_POS, []
