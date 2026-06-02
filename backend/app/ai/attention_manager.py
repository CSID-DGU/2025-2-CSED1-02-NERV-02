from pathlib import Path

from .bert_encoder import KcBertEncoder
from .attention_module import AttentionModule


class AttentionAIManager:
    def __init__(
        self,
        base_model_dir: str,
        modules_root: str,
        enabled_modules: list[str],
        max_length: int = 128,
    ):
        """
        공통 KcBERT encoder를 1회 로드하고,
        각 AI 모듈은 attention head만 로드한다.

        반환 구조는 기존 second_pass_filter.py와 맞추기 위해
        predict_one()에서 바로 {module_name: score} 형태를 반환한다.
        """
        self.encoder = KcBertEncoder(
            model_dir=base_model_dir,
            max_length=max_length,
        )
        
        self.device = self.encoder.device
        self.hidden_size = self.encoder.encoder.config.hidden_size
    
        self.modules: dict[str, AttentionModule] = {}

        for module_name in enabled_modules:
            normalized_module_name = module_name.strip().lower()
            module_dir = Path(modules_root) / normalized_module_name

            self.modules[normalized_module_name] = AttentionModule(
                module_name=normalized_module_name,
                module_dir=str(module_dir),
                hidden_size=self.hidden_size,
                device=self.device,
            )

    def predict_one(
        self,
        text: str,
        enabled_modules: set[str] | None = None,
    ) -> dict[str, float]:
        """
        기존 _call_ai_model()과 동일하게 score dict만 반환한다.

        반환 예:
        {
            "sexual": 0.97,
            "spam": 0.12,
            "pii": 0.03
        }

        detected module 판단은 risk_scorer.py에서 second_pass_scores를 기준으로 수행한다.
        """
        if enabled_modules is None:
            target_modules = set(self.modules.keys())
        else:
            target_modules = {
                module_name.strip().lower()
                for module_name in enabled_modules
                if module_name and module_name.strip()
            }

        if not target_modules:
            return {}

        encoded = self.encoder.encode_one(text)

        token_hidden = encoded["token_hidden"]
        attention_mask = encoded["attention_mask"]

        scores: dict[str, float] = {}

        for module_name in target_modules:
            module = self.modules.get(module_name)

            if module is None:
                continue

            score = module.predict_from_hidden(
                token_hidden=token_hidden,
                attention_mask=attention_mask,
            )

            scores[module_name] = float(score)

        return scores

    def update_one(
        self,
        module_name: str,
        text: str,
        label: int,
        save: bool = True,
    ) -> dict:
        """
        실시간 학습용.
        실행 중인 특정 module head만 업데이트한다.

        KcBERT encoder는 freeze되어 있고,
        AttentionModule 내부의 attention pooling + classifier만 업데이트된다.
        """
        normalized_module_name = module_name.strip().lower()

        if normalized_module_name not in self.modules:
            raise ValueError(f"로드되지 않은 module입니다: {normalized_module_name}")

        encoded = self.encoder.encode_one(text)

        token_hidden = encoded["token_hidden"]
        attention_mask = encoded["attention_mask"]

        return self.modules[normalized_module_name].update_from_hidden(
            token_hidden=token_hidden,
            attention_mask=attention_mask,
            label=label,
            save=save,
        )