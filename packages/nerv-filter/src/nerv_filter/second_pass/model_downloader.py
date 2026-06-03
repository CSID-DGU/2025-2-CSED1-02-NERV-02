"""HuggingFace 모델 다운로드 + encoder-only 변환.

처음 호출 시 HF 에서 모델을 받아 ``local_dir`` 에 encoder-only 모델로 저장한다.
이미 변환 완료 마커(`.encoder_only`)가 있으면 그대로 사용.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_REQUIRED_BASE_FILES = [
    "config.json",
    "tokenizer_config.json",
]

_ENCODER_ONLY_MARKER = ".encoder_only"


def is_model_dir_ready(model_dir: str) -> bool:
    path = Path(model_dir)
    if not path.exists():
        return False
    required_ok = all((path / filename).exists() for filename in _REQUIRED_BASE_FILES)
    encoder_only_ok = (path / _ENCODER_ONLY_MARKER).exists()
    return required_ok and encoder_only_ok


def _default_local_dir(repo_id: str) -> Path:
    """SDK 내부 기본 캐시 경로 — 사용자가 local_dir 를 지정하지 않은 경우."""
    sdk_root = Path(__file__).resolve().parent.parent      # nerv_filter/
    safe_name = repo_id.replace("/", "__")
    return sdk_root / "models" / "hf_cache" / safe_name


def ensure_hf_snapshot_downloaded(
    repo_id: str,
    local_dir: str | None = None,
    token: str | None = None,
    revision: str | None = None,
) -> str:
    """HuggingFace 모델 → 로컬 encoder-only 디렉토리 보장.

    Args:
        repo_id: HF 모델 ID (예: ``beomi/kcbert-large``).
        local_dir: 저장 경로. None 이면 SDK 내부 캐시.
        token: HF 토큰 (private repo 접근용).
        revision: branch/tag/commit SHA.

    Returns:
        encoder-only 모델 디렉토리 경로 (str).
    """
    target = Path(local_dir) if local_dir else _default_local_dir(repo_id)

    if is_model_dir_ready(str(target)):
        logger.info("[HF MODEL] 로컬 encoder-only 모델 사용: %s", target)
        return str(target)

    from huggingface_hub import snapshot_download
    from transformers import AutoModel, AutoTokenizer

    logger.info("[HF MODEL] HuggingFace 에서 모델 다운로드 시작: %s", repo_id)
    logger.info("[HF MODEL] 최종 저장 위치: %s", target)

    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "hf_snapshot"

        snapshot_download(
            repo_id=repo_id,
            local_dir=str(tmp_path),
            token=token,
            revision=revision,
        )

        logger.info("[HF MODEL] 다운로드 완료: %s", tmp_path)
        logger.info("[HF MODEL] encoder-only 변환 시작")

        tokenizer = AutoTokenizer.from_pretrained(str(tmp_path))
        model = AutoModel.from_pretrained(str(tmp_path))

        target.mkdir(parents=True, exist_ok=True)
        tokenizer.save_pretrained(str(target))
        model.save_pretrained(str(target))

        marker_path = target / _ENCODER_ONLY_MARKER
        marker_path.write_text("encoder_only=true\n", encoding="utf-8")

    logger.info("[HF MODEL] encoder-only 모델 저장 완료: %s", target)
    return str(target)
