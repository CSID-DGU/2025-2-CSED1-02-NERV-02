import json
import os
import threading
from pathlib import Path
import logging

import torch
import torch.nn as nn
from torch.optim import AdamW

from .attention_head import MLPAttentionHead

logger = logging.getLogger(__name__)

class AttentionModule:
    def __init__(
        self,
        module_name: str,
        module_dir: str,
        hidden_size: int,
        device: torch.device,
        learning_rate: float = 1e-4,
        weight_decay: float = 0.01,
    ):
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

    @torch.no_grad()
    def predict_from_hidden(
        self,
        token_hidden: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> float:
        with self.lock:
            self.head.eval()

            logits = self.head(
                token_hidden=token_hidden,
                attention_mask=attention_mask,
            )

            score = torch.sigmoid(logits)[0].item()
            return float(score)

    def update_from_hidden(
        self,
        token_hidden: torch.Tensor,
        attention_mask: torch.Tensor,
        label: int,
        save: bool = True,
    ) -> dict:
        """
        실행 중인 head를 단일 샘플로 바로 업데이트한다.
        encoder는 frozen이고 token_hidden은 no_grad 상태로 계산된 값이다.
        """
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

            # optimizer.step() 이후의 점수를 보고 싶으면 한 번 더 forward
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
        """
        실행 중 저장 파일 깨짐 방지를 위해 임시 파일에 저장 후 replace한다.
        """
        self.module_dir.mkdir(parents=True, exist_ok=True)

        final_path = self.module_dir / "attention_head.pt"
        tmp_path = self.module_dir / "attention_head.tmp.pt"

        payload = {
            "pool_attention": self.head.pool_attention.state_dict(),
            "classifier": self.head.classifier.state_dict(),
        }

        torch.save(payload, tmp_path)
        os.replace(tmp_path, final_path)