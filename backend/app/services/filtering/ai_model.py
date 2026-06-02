import logging
from dataclasses import dataclass
from pathlib import Path

from app.core import config
from app.ai.attention_manager import AttentionAIManager

logger = logging.getLogger(__name__)

KCBERT_BASE_MODEL_DIR : str = "models/kcbert_large"
ATTENTION_MODULES_ROOT : str = "models/modules"

AI_MAX_LENGTH : int = 128

ENABLED_AI_MODULES: list[str] = [
    "basic",
    "sexual",
    "pii",
    "criticism",
    "politics",
    "spam",
    "family"
]

@dataclass
class AttentionModelBundle:
    manager: AttentionAIManager

def _get_enabled_modules() -> list[str]:
    modules_root = Path(ATTENTION_MODULES_ROOT)
    enabled_modules: list[str] = []

    for module_name in ENABLED_AI_MODULES:
        module_dir = modules_root / module_name
        head_path = module_dir / "attention_head.pt"
        config_path = module_dir / "attention_config.json"

        if head_path.exists() and config_path.exists():
            enabled_modules.append(module_name)
        else:
            logger.warning(
                "[AI MODEL] %s 모듈 파일이 없어 로드에서 제외합니다. path=%s",
                module_name,
                module_dir,
            )

    return enabled_modules

def load_attention_second_pass_models() -> AttentionModelBundle:
    logger.info("[AI MODEL] 2차 필터 모델 로드 시작")

    enabled_modules = _get_enabled_modules()

    if not enabled_modules:
        raise RuntimeError("[AI MODEL] 로드 가능한 attention 모듈이 없습니다.")

    manager = AttentionAIManager(
        base_model_dir=KCBERT_BASE_MODEL_DIR,
        modules_root=ATTENTION_MODULES_ROOT,
        enabled_modules=enabled_modules,
        max_length=AI_MAX_LENGTH,
    )

    logger.info("[AI MODEL] 2차 필터 모델 로드 완료: %s", enabled_modules)

    return AttentionModelBundle(manager=manager)

def load_all_second_pass_models() -> AttentionModelBundle:
    return load_attention_second_pass_models()