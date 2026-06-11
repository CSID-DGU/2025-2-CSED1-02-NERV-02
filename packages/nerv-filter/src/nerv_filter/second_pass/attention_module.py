"""AttentionModule — 한 카테고리의 head 인스턴스.

체크포인트 파일(`attention_head.pt`)을 로드하고,
encoder 가 만든 token hidden 으로 점수를 산출한다.
실시간 학습(update_from_hidden)도 가능.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from .attention_head import MLPAttentionHead

logger = logging.getLogger(__name__)


class AttentionModule:
    def __init__(
        self,
        module_name: str,
        module_dir: str,
        hidden_size: int,
        device,
        learning_rate: float = 1e-4,
        weight_decay: float = 0.01,
    ):
        import torch
        import torch.nn as nn
        from torch.optim import AdamW

        self.module_name = module_name
        self.module_dir = Path(module_dir)
        self.device = device
        logger.info("[AI MODULE] %s head device=%s", self.module_name, self.device)
        self.lock = threading.RLock()

        config_path = self.module_dir / "attention_config.json"
        head_path = self.module_dir / "attention_head.pt"

        if not config_path.exists():
            raise FileNotFoundError(f"attention_config.json 없음: {config_path}")
        if not head_path.exists():
            raise FileNotFoundError(f"attention_head.pt 없음: {head_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.head = MLPAttentionHead(
            hidden_size=hidden_size,
            attention_hidden_dim=int(self.config.get("attention_hidden_dim", 128)),
            classifier_hidden_dim=int(self.config.get("classifier_hidden_dim", 128)),
            dropout=float(self.config.get("dropout", 0.1)),
        ).to(self.device)

        checkpoint = torch.load(head_path, map_location=self.device)
        self.head.pool_attention.load_state_dict(checkpoint["pool_attention"])
        self.head.classifier.load_state_dict(checkpoint["classifier"])
        self.head.eval()

        self.optimizer = AdamW(
            self.head.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )
        self.criterion = nn.BCEWithLogitsLoss()

        self._torch = torch
        self._nn = nn

    def predict_from_hidden(self, token_hidden, attention_mask) -> float:
        torch = self._torch
        with self.lock, torch.no_grad():
            self.head.eval()
            logits = self.head(
                token_hidden=token_hidden,
                attention_mask=attention_mask,
            )
            score = torch.sigmoid(logits)[0].item()
            return float(score)

    def predict_with_attention(self, token_hidden, attention_mask) -> dict:
        """점수와 token attention evidence 계산용 원천값을 함께 반환."""
        torch = self._torch
        with self.lock, torch.no_grad():
            self.head.eval()
            logits, attn_weights = self.head(
                token_hidden=token_hidden,
                attention_mask=attention_mask,
                return_attention=True,
            )
            logit = float(logits[0].item())
            score = float(torch.sigmoid(logits)[0].item())
            attention = attn_weights[0].detach().cpu().tolist()
            return {
                "score": score,
                "logit": logit,
                "attention": attention,
            }

    def update_from_hidden(
        self,
        token_hidden,
        attention_mask,
        label: int,
        save: bool = True,
    ) -> dict:
        """실시간 학습 — encoder frozen 상태에서 head 만 한 샘플로 업데이트."""
        torch = self._torch
        with self.lock:
            self.head.train()

            labels = torch.tensor([label], dtype=torch.float, device=self.device)
            self.optimizer.zero_grad(set_to_none=True)

            logits = self.head(
                token_hidden=token_hidden.detach(),
                attention_mask=attention_mask,
            )
            loss = self.criterion(logits, labels)
            loss.backward()

            torch.nn.utils.clip_grad_norm_(
                self.head.parameters(),
                max_norm=1.0,
            )
            self.optimizer.step()

            with torch.no_grad():
                updated_logits = self.head(
                    token_hidden=token_hidden.detach(),
                    attention_mask=attention_mask,
                )
                score_after = torch.sigmoid(updated_logits)[0].item()

            self.head.eval()

            if save:
                self.save_head_atomic()

            return {
                "module": self.module_name,
                "loss": float(loss.detach().cpu().item()),
                "score_after_step": float(score_after),
            }

    def save_head_atomic(self) -> None:
        """임시 파일 → replace 로 안전 저장."""
        torch = self._torch
        self.module_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.module_dir / "attention_head.pt"
        tmp_path = self.module_dir / "attention_head.tmp.pt"

        payload = {
            "pool_attention": self.head.pool_attention.state_dict(),
            "classifier": self.head.classifier.state_dict(),
        }

        torch.save(payload, tmp_path)
        os.replace(tmp_path, final_path)
