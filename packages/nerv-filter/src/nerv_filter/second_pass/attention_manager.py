"""AttentionAIManager — 공유 encoder + 카테고리별 head 들.

KcBERT encoder 를 1회 로드하고, 각 카테고리 모듈은 attention head 만 보유.
한 텍스트에 대해 ``predict_one()`` 한 번이면 활성화된 모든 head 의 점수를 dict 로 반환한다.
"""
from __future__ import annotations

from pathlib import Path

from .attention_module import AttentionModule
from .bert_encoder import KcBertEncoder


class AttentionAIManager:
    def __init__(
        self,
        base_model_dir: str | None,
        modules_root: str,
        enabled_modules: list[str],
        max_length: int = 128,
        hf_repo_id: str = "beomi/kcbert-large",
        hf_token: str | None = None,
    ):
        self.encoder = KcBertEncoder(
            model_dir=base_model_dir,
            repo_id=hf_repo_id,
            hf_token=hf_token,
            max_length=max_length,
        )

        self.device = self.encoder.device
        self.hidden_size = self.encoder.encoder.config.hidden_size

        self.modules: dict[str, AttentionModule] = {}

        modules_root_path = Path(modules_root)
        for module_name in enabled_modules:
            normalized_module_name = module_name.strip().lower()
            module_dir = modules_root_path / normalized_module_name

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
        """텍스트 → ``{module_name: score}`` (0~1 sigmoid).

        Args:
            text: 분석할 텍스트.
            enabled_modules: 이 호출에만 활성화할 모듈 (None = 전체).
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

    def predict_one_with_details(
        self,
        text: str,
        enabled_modules: set[str] | None = None,
    ) -> dict[str, dict]:
        """텍스트 → 모듈별 score/logit/token evidence 상세."""
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
        tokens = encoded.get("tokens") or [[]]
        offsets = encoded.get("offset_mapping") or [[]]

        details: dict[str, dict] = {}
        for module_name in target_modules:
            module = self.modules.get(module_name)
            if module is None:
                continue
            raw = module.predict_with_attention(
                token_hidden=token_hidden,
                attention_mask=attention_mask,
            )
            positive_logit = max(float(raw["logit"]), 0.0)
            token_evidence = []
            for token, offset, attention in zip(tokens[0], offsets[0], raw["attention"], strict=False):
                if not offset or len(offset) != 2:
                    continue
                start, end = int(offset[0]), int(offset[1])
                if start == end:
                    continue
                token_evidence.append({
                    "token": token,
                    "start": start,
                    "end": end,
                    "evidence": float(attention) * positive_logit,
                })
            details[module_name] = {
                "score": float(raw["score"]),
                "logit": float(raw["logit"]),
                "token_evidence": token_evidence,
            }
        return details

    def update_one(
        self,
        module_name: str,
        text: str,
        label: int,
        save: bool = True,
    ) -> dict:
        """실시간 학습 — 특정 모듈 head 만 한 샘플로 업데이트."""
        normalized_module_name = module_name.strip().lower()
        if normalized_module_name not in self.modules:
            raise ValueError(f"로드되지 않은 모듈입니다: {normalized_module_name}")

        encoded = self.encoder.encode_one(text)
        token_hidden = encoded["token_hidden"]
        attention_mask = encoded["attention_mask"]

        return self.modules[normalized_module_name].update_from_hidden(
            token_hidden=token_hidden,
            attention_mask=attention_mask,
            label=label,
            save=save,
        )
