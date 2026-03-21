import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PolicyManager:
    def __init__(self):
        logger.info(f"[System] Policy Manager 로드")

    def decide_action(
        self,
        risk_score: float,
        filter_result: Dict[str, Any],
        user_security_level: int,
        user_risk_threshold: float
    ) -> Dict[str, Any]:
        
        # 1. 원문 추출 (없으면 빈 문자열)
        # 1차 필터링 결과 dict 안에 'original_text' 키가 있다고 가정
        original_text = filter_result.get('original_text', '') 
        
        # 2. 점수 미달이면 무조건 통과 (PASS)
        if risk_score < user_risk_threshold:
            return {
                "action": "PASS",  # <--- 그냥 이렇게 문자열로 씀
                "processed_text": original_text,
                "score": risk_score
            }

        # 3. 점수 초과 시 레벨별 처분
        final_action = "PASS"
        processed_text = original_text
        
        # 문자열 오타만 조심하면 이 방식이 제일 빠르고 편함
        if user_security_level == 1:   # 관찰
            final_action = "MASKING"
            processed_text = self._mask_text(original_text, filter_result.get('detected_words', []))
            
        elif user_security_level == 2: # 관대함
            final_action = "REVIEW_HUMAN"
            processed_text = "[관리자 검토 중인 메시지입니다]"
            
        elif user_security_level == 3: # 일반
            final_action = "AUTO_HIDE"
            processed_text = "[규정 위반으로 숨겨진 메시지입니다]"
            
        elif user_security_level == 4: # 적극
            final_action = "AUTO_HIDE"
            processed_text = "[규정 위반으로 숨겨진 메시지입니다]"
            
        elif user_security_level == 5: # 최대 보호
            final_action = "PERMANENT_DELETE"
            processed_text = "[삭제된 메시지입니다]"

        return {
            "action": final_action, 
            "processed_text": processed_text,
            "score": risk_score
        }

    def _mask_text(self, text: str, detected_words: List[Dict[str, str]]) -> str:
        """ 마스킹 처리 """
        masked_text = text
        for item in detected_words:
            word = item.get('word', '')
            if word:
                masked_text = masked_text.replace(word, "*" * len(word))
        return masked_text