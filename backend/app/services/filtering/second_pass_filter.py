import logging
import torch

from app.services.filtering.ai_model import load_all_second_pass_models

logger = logging.getLogger(__name__)


class SecondPassFilter:
    def __init__(self):
        self.models = load_all_second_pass_models()

    async def execute(self, first_pass_result: dict) -> dict:
        original_text = first_pass_result["original_text"]

        try:
            ai_scores = await self._call_ai_model(original_text)

            return {
                **first_pass_result,
                "second_pass_scores": ai_scores,
            }

        except Exception as e:
            logger.error(f"2차 필터링 중 오류 발생: {e}", exc_info=True)
            return first_pass_result

    async def _call_ai_model(self, text: str) -> dict:
        results = {}

        for model_type, bundle in self.models.items():
            inputs = bundle.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=256,
            )
            inputs = {k: v.to(bundle.model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = bundle.model(**inputs)
                logits = outputs.logits

                if logits.shape[-1] == 1:
                    score = torch.sigmoid(logits).item()
                else:
                    probs = torch.softmax(logits, dim=-1)
                    score = probs[:, 1].item()

            results[model_type.value] = float(score)

        return results