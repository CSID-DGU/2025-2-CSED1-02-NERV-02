"""2차 필터 탐지기 — KcBERT + attention head 기반.

설계 원칙: **절대 예외를 위로 던지지 않는다.**
- 모델 로드 실패 → ``is_active=False`` (NervFilter 는 1차만 사용)
- 개별 추론 실패 → 빈 점수 dict 반환
이로써 2차에 어떤 문제가 생겨도 1차 필터는 항상 동작한다.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .config import SecondPassConfig

logger = logging.getLogger(__name__)


class SecondPassDetector:
    """KcBERT encoder + attention head 들로 텍스트의 카테고리 점수를 산출.

    무거운 의존성(torch / transformers) 은 생성 시점에 import.
    """

    def __init__(self, config: SecondPassConfig):
        self.config = config
        self._manager = None
        self._active = False

        if not config.is_enabled:
            logger.info("[2차필터] 비활성 (models=%s)", config.models)
            return

        modules_root = Path(config.resolved_modules_root)
        available = self._filter_available_modules(modules_root, config.models)
        if not available:
            logger.warning(
                "[2차필터] 사용 가능한 모듈 체크포인트가 없습니다 (root=%s, 요청=%s) — 1차만",
                modules_root, config.models,
            )
            return

        try:
            from .attention_manager import AttentionAIManager

            self._manager = AttentionAIManager(
                base_model_dir=config.base_model_dir,
                modules_root=str(modules_root),
                enabled_modules=available,
                max_length=config.max_length,
                hf_repo_id=config.hf_repo_id,
                hf_token=config.hf_token,
            )
            self._active = True
            logger.info("[2차필터] 활성 — 로드된 모듈: %s", available)
        except Exception as e:
            logger.error("[2차필터] 로드 실패 — 1차 필터만 사용: %s", e, exc_info=True)
            self._manager = None
            self._active = False

    @staticmethod
    def _filter_available_modules(modules_root: Path, requested: list[str]) -> list[str]:
        """체크포인트가 실제 존재하는 모듈만 추림."""
        available: list[str] = []
        for name in requested:
            normalized = name.strip().lower()
            head = modules_root / normalized / "attention_head.pt"
            cfg = modules_root / normalized / "attention_config.json"
            if head.exists() and cfg.exists():
                available.append(normalized)
            else:
                logger.warning("[2차필터] 모듈 파일 없음, 제외: %s (path=%s)",
                               normalized, modules_root / normalized)
        return available

    @property
    def is_active(self) -> bool:
        """실제로 추론 가능한 상태."""
        return self._active

    def predict(self, text: str, enabled_modules: set[str] | None = None) -> dict[str, float]:
        """텍스트 → ``{module_name: score}`` (0~1).

        실패 시 빈 dict. 예외를 던지지 않음.
        """
        if not self._active or not text or self._manager is None:
            return {}
        try:
            return self._manager.predict_one(text, enabled_modules=enabled_modules)
        except Exception as e:
            logger.warning("[2차필터] 추론 실패 — 결과 없음 처리: %s", e)
            return {}

    def detect(self, text: str, enabled_modules: set[str] | None = None) -> list[str]:
        """이전 API 호환 — threshold 이상인 카테고리 이름 리스트만 반환."""
        scores = self.predict(text, enabled_modules=enabled_modules)
        return [name for name, score in scores.items() if score >= self.config.threshold]

    def update(self, module_name: str, text: str, label: int, save: bool = True) -> dict:
        """실시간 학습 — 한 카테고리 head 를 단일 샘플로 업데이트.

        Raises:
            RuntimeError: 2차 비활성 상태.
            ValueError: 미로드 모듈.
        """
        if not self._active or self._manager is None:
            raise RuntimeError("2차 필터가 활성화되지 않았습니다.")
        return self._manager.update_one(module_name, text, label, save=save)
