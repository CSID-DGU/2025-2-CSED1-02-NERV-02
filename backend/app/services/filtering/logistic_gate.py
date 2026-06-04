import logging
import pickle
from pathlib import Path
from typing import Dict, Iterable

logger = logging.getLogger(__name__)


DEFAULT_GATE_THRESHOLD = 0.3

MODULE_MODEL_FILENAMES = {
    "basic": "basic_logistic_model.pkl",
    "criticism": "criticism_logistic_model.pkl",
    "family": "family_logistic_model.pkl",
    "pii": "pii_logistic_model.pkl",
    "politics": "politics_logistic_model.pkl",
    "sexual": "sexual_logistic_model.pkl",
    "spam": "spam_logistic_model.pkl",
}


class LogisticGateFilter:
    """
    KcBERT 2차 AI 앞단에서 사용할 가벼운 gate 모델.

    역할:
    - 각 모듈별 TF-IDF + LogisticRegression 모델로 positive 확률 계산
    - threshold 이상인 모듈만 2차 AI로 전달
    """

    def __init__(
        self,
        model_dir: str = "models/logistic_gate",
        threshold: float = DEFAULT_GATE_THRESHOLD,
    ):
        self.model_dir = Path(model_dir)
        self.threshold = threshold
        self.models = self._load_models()

        logger.info(
            "[LOGISTIC GATE] 로드 완료: %s",
            sorted(self.models.keys()),
        )

    def _load_models(self) -> Dict[str, object]:
        models: Dict[str, object] = {}

        for module_name, filename in MODULE_MODEL_FILENAMES.items():
            path = self.model_dir / filename

            if not path.exists():
                logger.warning("[LOGISTIC GATE] 모델 없음: %s", path)
                continue

            with path.open("rb") as f:
                models[module_name] = pickle.load(f)

            logger.info("[LOGISTIC GATE] %s 로드: %s", module_name, path)

        return models

    def predict_scores(
        self,
        text: str,
        enabled_modules: Iterable[str] | None = None,
    ) -> Dict[str, float]:
        if enabled_modules is None:
            target_modules = set(self.models.keys())
        else:
            target_modules = {
                module.strip().lower()
                for module in enabled_modules
                if module and module.strip()
            }

        scores: Dict[str, float] = {}

        for module_name in target_modules:
            model = self.models.get(module_name)

            if model is None:
                continue

            proba = model.predict_proba([text])[0][1]
            scores[module_name] = float(proba)

        return scores

    def select_modules(
        self,
        text: str,
        enabled_modules: Iterable[str] | None = None,
    ) -> tuple[set[str], Dict[str, float]]:
        scores = self.predict_scores(
            text=text,
            enabled_modules=enabled_modules,
        )

        selected = {
            module_name
            for module_name, score in scores.items()
            if score >= self.threshold
        }

        return selected, scores