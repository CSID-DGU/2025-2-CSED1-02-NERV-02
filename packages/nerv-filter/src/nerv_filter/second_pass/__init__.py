"""2차 필터 — KcBERT + per-category attention head 기반 AI 탐지 (선택 기능).

torch / transformers / huggingface-hub 가 필요하므로 ``pip install nerv-filter[ai]``
로 설치한다. 미설치 또는 비활성 시 NervFilter 는 1차 필터만으로 정상 동작한다
(graceful degradation).

Public API:
    SecondPassConfig        설정 dataclass + ``from_env`` 헬퍼
    SecondPassModelType     카테고리 enum
    SecondPassDetector      KcBERT + head 기반 추론기 (predict / detect / update)
"""
from .config import SecondPassConfig, SecondPassModelType
from .detector import SecondPassDetector

__all__ = ["SecondPassConfig", "SecondPassModelType", "SecondPassDetector"]
