"""
시스템 사전(dic.json) 로더.

dic.json 스키마 (v2):
{
  "category": {
    "root_word": {"pos": "NNG|VV|VA|...", "variants": [...]},
    ...
  }
}

- flat word set: FirstPassFilter가 set 매칭에 사용 (root + variants 모두 포함)
- KiwiUserWord 리스트: KiwiEngine이 add_user_word로 등록 (형태소 경계 인식용)
  · root_word는 등록된 pos 그대로
  · variants는 표기 변형이므로 항상 NNG로 등록 (활용형 필요 없음)
"""
import json
import logging
from pathlib import Path

from .kiwi_engine import KiwiUserWord

logger = logging.getLogger(__name__)

_DIC_PATH = Path(__file__).resolve().parents[3] / "data" / "dic.json"

_DEFAULT_POS = "NNG"
_VARIANT_POS = "NNG"
_ROOT_SCORE = 5.0
_VARIANT_SCORE = 3.0


def load_system_dict() -> tuple[set[str], list[KiwiUserWord]]:
    """dic.json 을 읽어 (flat word set, Kiwi user_word 엔트리 리스트) 반환."""
    with open(_DIC_PATH, encoding="utf-8") as f:
        data = json.load(f)

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
                user_words.append(KiwiUserWord(word=v, pos=_VARIANT_POS, score=_VARIANT_SCORE))

    logger.info(
        f"[SystemDictLoader] 시스템 사전 로드 완료: {len(words)}개 단어, "
        f"Kiwi user_word {len(user_words)}건"
    )
    return words, user_words


def _parse_entry(payload) -> tuple[str, list[str]]:
    """엔트리 포맷 정규화. dict 또는 list 모두 허용."""
    if isinstance(payload, dict):
        pos = payload.get("pos", _DEFAULT_POS)
        variants = payload.get("variants", [])
        return pos, list(variants)
    if isinstance(payload, list):
        return _DEFAULT_POS, list(payload)
    return _DEFAULT_POS, []
