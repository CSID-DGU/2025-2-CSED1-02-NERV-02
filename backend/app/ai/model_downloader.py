import logging
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import snapshot_download
from transformers import AutoModel, AutoTokenizer

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


def ensure_hf_snapshot_downloaded(
    repo_id: str,
    local_dir: str,
    token: str | None = None,
    revision: str | None = None,
) -> str:
    """
    최초 실행 시 Hugging Face repo에서 모델을 다운로드한 뒤,
    AutoModel 기준 encoder-only 모델로 local_dir에 저장한다.

    이미 local_dir에 encoder-only 모델이 있으면 그대로 사용한다.

    주의:
    - 기존 local_dir이 encoder-only가 아닌 상태로 존재하면 자동 덮어쓰기하지 않는다.
    - 그런 경우 사용자가 직접 local_dir을 삭제한 뒤 다시 실행해야 한다.
    """
    local_path = Path(local_dir)

    if is_model_dir_ready(str(local_path)):
        logger.info("[HF MODEL] 로컬 encoder-only 모델 사용: %s", local_path)
        return str(local_path)

    logger.info("[HF MODEL] Hugging Face에서 모델 다운로드 시작: %s", repo_id)
    logger.info("[HF MODEL] 최종 저장 위치: %s", local_path)

    local_path.parent.mkdir(parents=True, exist_ok=True)

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

        # local_path는 없거나 비어 있어야 한다.
        local_path.mkdir(parents=True, exist_ok=True)

        tokenizer.save_pretrained(str(local_path))
        model.save_pretrained(str(local_path))

        marker_path = local_path / _ENCODER_ONLY_MARKER
        marker_path.write_text("encoder_only=true\n", encoding="utf-8")

    logger.info("[HF MODEL] encoder-only 모델 저장 완료: %s", local_path)

    return str(local_path)