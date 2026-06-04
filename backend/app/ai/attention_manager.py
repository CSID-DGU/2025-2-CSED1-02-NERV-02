from pathlib import Path
import re

import torch

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

    def mask_by_input_gradient(
        self,
        text: str,
        target_modules: list[str] | set[str],
        attribution_threshold: float = 0.3,
        top_k: int = 10,
        fallback_top_n: int = 1,
        mask_char: str = "*",
    ) -> dict:
        """
        MEDIUM AI 탐지 시 사용한다.

        각 target module에 대해 Input Embedding Gradient × Input을 계산하고,
        normalized attribution이 threshold 이상인 토큰을 원문에서 마스킹한다.

        threshold 이상 토큰이 하나도 없으면 fallback_top_n개를 마스킹한다.
        """
        normalized_modules = [
            module_name.strip().lower()
            for module_name in target_modules
            if module_name and module_name.strip()
        ]

        all_evidence_tokens: list[dict] = []

        for module_name in normalized_modules:
            if module_name not in self.modules:
                continue

            evidence = self._attribute_input_gradient_for_module(
                text=text,
                module_name=module_name,
                top_k=top_k,
            )

            selected = [
                item
                for item in evidence["tokens"]
                if item["embed_attr"] >= attribution_threshold
            ]

            if not selected and fallback_top_n > 0:
                selected = evidence["tokens"][:fallback_top_n]

            for item in selected:
                all_evidence_tokens.append(
                    {
                        "module": module_name,
                        "token": item["token"],
                        "embed_attr": item["embed_attr"],
                        "raw_attr": item["raw_attr"],
                        "attention": item["attention"],
                    }
                )

        masked_text = self._mask_text_by_tokens(
            text=text,
            tokens=[item["token"] for item in all_evidence_tokens],
            mask_char=mask_char,
        )

        return {
            "processed_text": masked_text,
            "attribution_threshold": attribution_threshold,
        }

    def _attribute_input_gradient_for_module(
        self,
        text: str,
        module_name: str,
        top_k: int = 10,
    ) -> dict:
        """
        기존 실험에서 최종 선택한 Input Embedding Gradient × Input 방식.

        계산:
        1. input_ids → input embeddings
        2. inputs_embeds 기준으로 KcBERT forward
        3. module head로 logit 계산
        4. target_logit.backward()
        5. grad × input
        6. token별 abs attribution
        7. 문장 내부 정규화
        """
        module = self.modules[module_name]

        self.encoder.encoder.eval()
        module.head.eval()

        encoding = self.encoder.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.encoder.max_length,
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        token_type_ids = encoding.get("token_type_ids")
        if token_type_ids is not None:
            token_type_ids = token_type_ids.to(self.device)

        embedding_layer = self.encoder.encoder.get_input_embeddings()
        inputs_embeds = embedding_layer(input_ids)

        inputs_embeds = inputs_embeds.detach()
        inputs_embeds.requires_grad_(True)

        self.encoder.encoder.zero_grad(set_to_none=True)
        module.head.zero_grad(set_to_none=True)

        encoder_kwargs = {
            "inputs_embeds": inputs_embeds,
            "attention_mask": attention_mask,
        }

        if token_type_ids is not None:
            encoder_kwargs["token_type_ids"] = token_type_ids

        outputs = self.encoder.encoder(**encoder_kwargs)
        token_hidden = outputs.last_hidden_state

        with module.lock:
            logits, attn_weights = module.head(
                token_hidden=token_hidden,
                attention_mask=attention_mask,
                return_attention=True,
            )

            score = torch.sigmoid(logits)[0]
            target_logit = logits[0]

            target_logit.backward()

        gradients = inputs_embeds.grad

        if gradients is None:
            raise RuntimeError("Input Gradient 계산 중 gradients가 생성되지 않았습니다.")

        grad_x_input = gradients * inputs_embeds

        token_raw_scores = grad_x_input.sum(dim=-1).squeeze(0)
        token_abs_scores = token_raw_scores.abs()

        tokens = self.encoder.tokenizer.convert_ids_to_tokens(
            input_ids[0].detach().cpu().tolist()
        )

        raw_scores = token_raw_scores.detach().cpu().tolist()
        abs_scores = token_abs_scores.detach().cpu().tolist()
        attn_scores = attn_weights[0].detach().cpu().tolist()
        masks = attention_mask[0].detach().cpu().tolist()

        items = []

        for token, raw_attr, abs_attr, attention, mask in zip(
            tokens,
            raw_scores,
            abs_scores,
            attn_scores,
            masks,
        ):
            if mask == 0:
                continue

            if token in ["[CLS]", "[SEP]", "[PAD]"]:
                continue

            items.append(
                {
                    "token": token,
                    "raw_attr": float(raw_attr),
                    "score": float(abs_attr),
                    "attention": float(attention),
                }
            )

        merged_items = self._merge_wordpiece_tokens(items)

        total = sum(item["score"] for item in merged_items)

        for item in merged_items:
            item["embed_attr"] = item["score"] / total if total > 0 else 0.0

        top_items = sorted(
            merged_items,
            key=lambda x: x["embed_attr"],
            reverse=True,
        )[:top_k]

        return {
            "module": module_name,
            "text": text,
            "score": float(score.detach().cpu().item()),
            "tokens": top_items,
        }

    def _merge_wordpiece_tokens(self, token_items: list[dict]) -> list[dict]:
        merged = []

        for item in token_items:
            token = item["token"]

            if token in ["[CLS]", "[SEP]", "[PAD]"]:
                continue

            if token.startswith("##") and merged:
                merged[-1]["token"] += token[2:]
                merged[-1]["score"] += item.get("score", 0.0)
                merged[-1]["raw_attr"] += item.get("raw_attr", 0.0)
                merged[-1]["attention"] += item.get("attention", 0.0)
            else:
                merged.append(
                    {
                        "token": token,
                        "score": item.get("score", 0.0),
                        "raw_attr": item.get("raw_attr", 0.0),
                        "attention": item.get("attention", 0.0),
                    }
                )

        return merged

    def _mask_text_by_tokens(
        self,
        text: str,
        tokens: list[str],
        mask_char: str = "*",
    ) -> str:
        masked = text

        unique_tokens = sorted(
            {token for token in tokens if token and token.strip()},
            key=len,
            reverse=True,
        )

        for token in unique_tokens:
            replacement = mask_char * len(token)
            masked = re.sub(re.escape(token), replacement, masked)

        return masked