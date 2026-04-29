import logging
import os
from dataclasses import dataclass
from enum import Enum
from app.core import settings

from transformers import AutoModelForSequenceClassification, AutoTokenizer
from transformers.utils import logging as hf_logging


logger = logging.getLogger(__name__)
hf_logging.set_verbosity_error()


class SecondPassModelType(str, Enum):
    SPAM = "spam"
    PII = "pii"
    POLITICS = "politics"
    CRITICISM = "criticism"
    BASIC = "basic"
    SEXUAL = "sexual"


@dataclass
class ModelBundle:
    model_type: SecondPassModelType
    repo_id: str
    tokenizer: object
    model: object


def build_repo_id(model_type: SecondPassModelType) -> str:
    if not settings.HF_MODEL_OWNER:
        raise ValueError("HF_MODEL_OWNER 환경변수가 설정되지 않았습니다.")
    return f"{settings.HF_MODEL_OWNER}/kcbert-{model_type.value}-classifier"


def load_single_model(model_type: SecondPassModelType) -> ModelBundle:
    repo_id = build_repo_id(model_type)

    tokenizer = AutoTokenizer.from_pretrained(
        repo_id,
        token=settings.HF_TOKEN,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        repo_id,
        token=settings.HF_TOKEN,
    )
    model.eval()

    logger.info(f"[AI MODEL] {model_type.value} 로드 완료")

    return ModelBundle(
        model_type=model_type,
        repo_id=repo_id,
        tokenizer=tokenizer,
        model=model,
    )


def load_all_second_pass_models() -> dict[SecondPassModelType, ModelBundle]:
    logger.info("[AI MODEL] 2차 필터 모델 로드 시작")

    models = {
        model_type: load_single_model(model_type)
        for model_type in SecondPassModelType
    }

    logger.info(f"[AI MODEL] 전체 모델 로드 완료 ({len(models)}개)")
    return models