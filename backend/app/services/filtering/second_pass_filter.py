import logging

from app.schemas.enums import FilterStatus, WordType

logger = logging.getLogger(__name__)


class SecondPassFilter:
    def __init__(self):
        # TODO: AI 모델 초기화
        pass

    async def execute(self, first_pass_result: dict) -> dict:
        original_text = first_pass_result["original_text"]
        status = first_pass_result["status"]
        detected_words = list(first_pass_result["detected_words"])
        masked_text = first_pass_result["masked_text"]

        try:
            # TODO: AI 모델 호출
            # ai_detected_items = await self._call_ai_model(masked_text)
            # 예시 반환 형식:
            # [{"word": "문제 구문", "type": WordType.AI_AGGRESSION}, ...]
            ai_detected_items = []

            if ai_detected_items:
                status = FilterStatus.FILTERED_BY_SECOND_PASS
                for item in ai_detected_items:
                    word = item["word"]
                    if word not in masked_text:
                        continue
                    detected_words.append({"word": word,"type": item["type"],})
                    masked_text = masked_text.replace(word, "__S__")

            return {
                "original_text": original_text,
                "status": status,
                "detected_words": detected_words,
                "masked_text": masked_text,
            }

        except Exception as e:
            logger.error(f"2차 필터링 중 오류 발생: {e}", exc_info=True)
            return first_pass_result

    # TODO: AI 모델 호출 메서드 구현
    # async def _call_ai_model(self, text: str) -> list[dict]:
    #     """
    #     AI 모델을 호출하여 탐지 결과를 반환합니다.
    #     반환 형식: [{"word": str, "type": WordType}]
    #     """
    #     raise NotImplementedError