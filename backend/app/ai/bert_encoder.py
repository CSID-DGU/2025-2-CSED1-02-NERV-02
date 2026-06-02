# app/ml/attention_ai/shared_encoder.py
import logging
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModel

from app.core import config
from app.ai.model_downloader import ensure_hf_snapshot_downloaded

logger = logging.getLogger(__name__)
KCBERT_REPO_ID: str = "beomi/kcbert-large"

class KcBertEncoder:
    def __init__(
        self,
        model_dir: str | None = None,
        max_length: int = 128,
    ):
        self.repo_id = KCBERT_REPO_ID
        self.model_dir = model_dir
        self.max_length = max_length

        # 없으면 Hugging Face에서 다운로드, 있으면 로컬 사용
        resolved_model_dir = ensure_hf_snapshot_downloaded(
            repo_id=self.repo_id,
            local_dir=self.model_dir
        )

        self.model_dir = Path(resolved_model_dir)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("[KcBERT] device=%s", self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
        self.encoder = AutoModel.from_pretrained(str(self.model_dir)).to(self.device)

        self.encoder.eval()

        for param in self.encoder.parameters():
            param.requires_grad = False

    def encode_texts(self, texts: list[str]):
        encoding = self.tokenizer(
            texts,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        token_type_ids = encoding.get("token_type_ids")
        if token_type_ids is not None:
            token_type_ids = token_type_ids.to(self.device)

        with torch.no_grad():
            outputs = self.encoder(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
            )

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
            "token_hidden": outputs.last_hidden_state,
        }

    def encode_one(self, text: str):
        return self.encode_texts([text])