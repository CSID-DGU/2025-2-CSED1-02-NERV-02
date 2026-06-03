"""2차 필터 설정 — KcBERT + per-category attention head 구조."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SecondPassModelType(str, Enum):
    """2차 모듈 종류. 각 값은 ``models/modules/<name>/`` 디렉토리에 대응."""

    BASIC = "basic"          # 일반 욕설/비속어
    SEXUAL = "sexual"        # 성적 표현
    SPAM = "spam"            # 스팸/광고
    POLITICS = "politics"    # 정치
    PII = "pii"              # 개인정보
    CRITICISM = "criticism"  # 비판/저격
    FAMILY = "family"        # 가족 관련 모욕


def _sdk_root() -> Path:
    """SDK 루트 (``nerv_filter/``) 경로."""
    return Path(__file__).resolve().parent.parent


def _default_modules_root() -> Path:
    """SDK 에 동봉된 attention head 체크포인트 루트."""
    return _sdk_root() / "models" / "modules"


_ALL_MODULES: list[str] = [m.value for m in SecondPassModelType]


@dataclass
class SecondPassConfig:
    """2차 필터 설정.

    Args:
        models: 활성화할 카테고리 이름들. 빈 리스트면 2차 비활성 (1차만).
        base_model_dir: KcBERT encoder 로컬 캐시 경로. ``None`` 이면 SDK 기본 캐시 위치.
        modules_root: attention head 체크포인트 디렉토리 루트. ``None`` 이면 SDK 동봉 모델.
        threshold: 이 값 이상이면 해당 카테고리 탐지로 간주 (기본 0.8).
        max_length: 토크나이저 최대 길이.
        hf_repo_id: KcBERT HuggingFace 리포 (encoder 가 없을 때 다운로드).
        hf_token: 비공개 리포 접근용 토큰.
    """

    models: list[str] = field(default_factory=list)
    base_model_dir: str | None = None
    modules_root: str | None = None
    threshold: float = 0.8
    max_length: int = 128
    hf_repo_id: str = "beomi/kcbert-large"
    hf_token: str | None = None

    @property
    def is_enabled(self) -> bool:
        """설정상 2차를 켜려는 상태 (실제 로드 성공 여부는 ``Detector.is_active``)."""
        return bool(self.models)

    @property
    def resolved_modules_root(self) -> str:
        return self.modules_root or str(_default_modules_root())

    @classmethod
    def from_env(cls) -> SecondPassConfig:
        """환경변수에서 설정 로드.

        - ``SECOND_PASS_ENABLED``: ``false`` 면 강제 비활성 (킬스위치).
        - ``ENABLED_MODELS``: 쉼표 구분 모듈 (예: ``basic,sexual,spam``).
          ``ALL`` 또는 미지정이면 모든 모듈.
        - ``SECOND_PASS_THRESHOLD`` (기본 0.8)
        - ``SECOND_PASS_BASE_MODEL_DIR``: KcBERT 로컬 캐시 경로 (선택).
        - ``SECOND_PASS_MODULES_ROOT``: attention head 디렉토리 루트 (선택).
        - ``SECOND_PASS_MAX_LENGTH`` (기본 128)
        - ``SECOND_PASS_HF_REPO_ID`` (기본 beomi/kcbert-large)
        - ``HF_TOKEN``
        """
        enabled = os.environ.get("SECOND_PASS_ENABLED", "true").strip().lower()
        if enabled in ("false", "0", "no", "off"):
            return cls(models=[])

        raw = os.environ.get("ENABLED_MODELS", "ALL").strip()
        if not raw or raw.upper() == "ALL":
            models = list(_ALL_MODULES)
        else:
            models = [m.strip().lower() for m in raw.split(",") if m.strip()]

        def _clean(v: str | None) -> str | None:
            return v.strip().strip('"').strip("'") if v else None

        try:
            threshold = float(os.environ.get("SECOND_PASS_THRESHOLD", "0.8"))
        except ValueError:
            threshold = 0.8

        try:
            max_length = int(os.environ.get("SECOND_PASS_MAX_LENGTH", "128"))
        except ValueError:
            max_length = 128

        return cls(
            models=models,
            base_model_dir=_clean(os.environ.get("SECOND_PASS_BASE_MODEL_DIR")),
            modules_root=_clean(os.environ.get("SECOND_PASS_MODULES_ROOT")),
            threshold=threshold,
            max_length=max_length,
            hf_repo_id=_clean(os.environ.get("SECOND_PASS_HF_REPO_ID")) or "beomi/kcbert-large",
            hf_token=_clean(os.environ.get("HF_TOKEN")),
        )
