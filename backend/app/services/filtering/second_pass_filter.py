import logging

from app.services.filtering.ai_model import load_all_second_pass_models

logger = logging.getLogger(__name__)


class SecondPassFilter:
    def __init__(self):
        self.model_bundle = load_all_second_pass_models()
        self.ai_manager = self.model_bundle.manager

    async def execute(
        self,
        first_pass_result: dict,
        enabled_modules: str = "ALL",
    ) -> dict:
        original_text = first_pass_result["original_text"]

        enabled = self._parse_enabled_modules(enabled_modules)

        try:
            ai_scores = await self._call_ai_model(original_text, enabled)

            return {
                **first_pass_result,
                "second_pass_scores": ai_scores,
            }

        except Exception as e:
            logger.error(f"2차 필터링 중 오류 발생: {e}", exc_info=True)
            return first_pass_result

    def _parse_enabled_modules(self, enabled_modules: str) -> set[str] | None:
        if not enabled_modules:
            return set()

        raw = enabled_modules.strip()

        if raw.upper() == "ALL":
            return None

        return {
            module_name.strip().lower()
            for module_name in raw.split(",")
            if module_name.strip()
        }

    async def _call_ai_model(
        self,
        text: str,
        enabled_modules: set[str] | None,
    ) -> dict[str, float]:
        return self.ai_manager.predict_one(
            text=text,
            enabled_modules=enabled_modules,
        )

    def mask_by_ai_evidence(
        self,
        text: str,
        target_modules: list[str] | set[str],
        attribution_threshold: float = 0.15,
        top_k: int = 10,
        fallback_top_n: int = 1,
    ) -> dict:
        return self.ai_manager.mask_by_input_gradient(
            text=text,
            target_modules=target_modules,
            attribution_threshold=attribution_threshold,
            top_k=top_k,
            fallback_top_n=fallback_top_n,
        )

    async def update_ai_module(
        self,
        module_name: str,
        text: str,
        label: int,
        save: bool = True,
    ) -> dict:
        return self.ai_manager.update_one(
            module_name=module_name,
            text=text,
            label=label,
            save=save,
        )