"""KcBERT encoder — frozen 공유 인코더.

여러 카테고리 head 가 같은 token hidden 을 재사용해 추론 비용을 1회로 압축한다.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .model_downloader import ensure_hf_snapshot_downloaded

logger = logging.getLogger(__name__)

KCBERT_DEFAULT_REPO_ID: str = "beomi/kcbert-large"


class KcBertEncoder:
    """KcBERT 인코더 래퍼.

    - 로컬 디렉토리에 encoder-only 모델이 있으면 그대로 사용
    - 없으면 HuggingFace 에서 다운로드 후 encoder-only 로 저장
    - 모든 파라미터 frozen (추론 전용)
    """

    def __init__(
        self,
        model_dir: str | None = None,
        repo_id: str = KCBERT_DEFAULT_REPO_ID,
        hf_token: str | None = None,
        max_length: int = 128,
    ):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.repo_id = repo_id
        self.max_length = max_length

        resolved_model_dir = ensure_hf_snapshot_downloaded(
            repo_id=self.repo_id,
            local_dir=model_dir,
            token=hf_token,
        )
        self.model_dir = Path(resolved_model_dir)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("[KcBERT] device=%s model_dir=%s", self.device, self.model_dir)

        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
        self.encoder = AutoModel.from_pretrained(str(self.model_dir)).to(self.device)

        self.encoder.eval()
        for param in self.encoder.parameters():
            param.requires_grad = False

        self._torch = torch

    def encode_texts(self, texts: list[str]) -> dict:
        torch = self._torch

        encoding_kwargs = {
            "truncation": True,
            "padding": "max_length",
            "max_length": self.max_length,
            "return_tensors": "pt",
        }
        try:
            encoding = self.tokenizer(
                texts,
                return_offsets_mapping=True,
                **encoding_kwargs,
            )
            offset_mapping = encoding.pop("offset_mapping")
        except NotImplementedError:
            encoding = self.tokenizer(texts, **encoding_kwargs)
            offset_mapping = None

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
            "tokens": [
                self.tokenizer.convert_ids_to_tokens(ids)
                for ids in encoding["input_ids"].detach().cpu().tolist()
            ],
            "offset_mapping": offset_mapping.detach().cpu().tolist()
            if offset_mapping is not None
            else None,
        }

    def encode_one(self, text: str) -> dict:
        return self.encode_texts([text])
