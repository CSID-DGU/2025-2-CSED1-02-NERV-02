import re
import logging
from typing import Dict, Any
from dataclasses import dataclass
from app.schemas.enums import WordType

logger = logging.getLogger(__name__)

@dataclass
class _Weights:
    BASE_SYSTEM: float = 0.4            # 기본 점수
    BASE_BLACKLIST: float = 0.7         # 블랙리스트 단어 포함 시 기본 점수

    COUNT_BONUS: float = 0.1            # 욕설 개수당 가산점
    COUNT_MAX: float = 0.4              # 개수 가산점 상한선

    DENSITY_BONUS: float = 0.2          # 밀도(전체 길이 대비 욕설 비중) 가산점

    CONSECUTIVE_BONUS: float = 0.15     # 연속된 욕설 한 쌍당 가산점
    CONSECUTIVE_LEN_MAX: float = 0.3    # 연속성 점수 중간 상한
    CONSECUTIVE_MAX: float = 0.4        # 연속성 점수 최종 상한선

class RiskScorer:
    def __init__(self):
        self.weights = _Weights()
        logger.info("[System] Risk Scorer(위험도 분석기) 로드 완료")

    def execute(self, filter_result: Dict[str, Any]) -> float:
        """
        1차 필터링 결과를 바탕으로 위험도 점수(0.0 ~ 1.0)를 계산합니다.
        """
        # 1. 데이터 추출
        detected_words = filter_result.get('detected_words', [])
        masked_text = filter_result.get('masked_text', "")
        
        if not detected_words:
            return 0.0
        
        # 2. 기본 점수 (Base Score)
        has_blacklist = any(item['type'] == WordType.USER_BLACKLIST for item in detected_words)
        if has_blacklist:
            total_score = self.weights.BASE_BLACKLIST
        else:
            total_score = self.weights.BASE_SYSTEM

        # 3. 가중치 계산
        
        # (A) 개수 (Quantity)
        count = len(detected_words)
        total_score += min((count - 1) * self.weights.COUNT_BONUS, self.weights.COUNT_MAX)
        
        # (B) 밀도 (Density)
        text_len = len(masked_text.replace(" ", ""))
        if text_len > 0:
            detected_words_len = sum(len(item['word']) for item in detected_words)
            density = detected_words_len / text_len
            if density > 0.4:
                total_score += self.weights.DENSITY_BONUS

        # (C) 연속성 (Consecutive Degree)
        # "__B__" 또는 "__F__" 토큰이 2개 이상 연속으로 나오는 시퀀스 탐색
        sequences = re.findall(r'(?:__[BF]__\s*){2,}', masked_text)
        
        consecutive_score = 0.0
        for seq in sequences:
            # 발견된 시퀀스 안에서 토큰(__F__, __B__) 수 계산
            seq_len = len(re.findall(r'__[BF]__', seq))
            if seq_len >= 2:
                consecutive_score += min(self.weights.CONSECUTIVE_BONUS * (seq_len - 1), self.weights.CONSECUTIVE_LEN_MAX)
        
        total_score += min(consecutive_score, self.weights.CONSECUTIVE_MAX)

        # 4. 최종 마무리
        return min(round(total_score, 2), 1.0)