import re

class RiskScorer:
    def __init__(self):
        self.weights = {
            'BASE_SYSTEM': 0.4,      # 기본 점수
            'BASE_BLACKLIST': 0.7,   # 블랙리스트 단어 포함 시 기본 점수
            
            'COUNT_BONUS': 0.1,     # 욕설 개수당 가산점
            'COUNT_MAX': 0.4,       # 개수 가산점 상한선
            
            'DENSITY_BONUS': 0.2,   # 밀도(전체 길이 대비 욕설 비중) 가산점
            
            'CONSECUTIVE_BONUS': 0.15, # 연속된 욕설 한 쌍당 가산점
            'CONSECUTIVE_LEN_MAX': 0.3, # 연속성 점수 중간 상한
            'CONSECUTIVE_MAX': 0.4    # 연속성 점수 최종 상한선
        }
        print("[System] Risk Scorer(위험도 분석기) 로드 완료")

    def execute(self, filter_result: dict) -> float:
        """
        1차 필터링 결과를 바탕으로 위험도 점수(0.0 ~ 1.0)를 계산합니다.
        """
        # 1. 데이터 추출
        detected_words = filter_result.get('detected_words', [])
        text_for_filtering = filter_result.get('text_for_filtering', "")
        
        if not detected_words:
            return 0.0
        
        # 2. 기본 점수 (Base Score)
        has_blacklist = any(item['type'] == 'USER_BLACKLIST' for item in detected_words)
        if has_blacklist:
            total_score = self.weights['BASE_BLACKLIST']
        else:
            total_score = self.weights['BASE_SYSTEM']

        # 3. 가중치 계산
        
        # (A) 개수 (Quantity)
        count = len(detected_words)
        total_score += min((count - 1) * self.weights['COUNT_BONUS'], self.weights['COUNT_MAX'])
        
        # (B) 밀도 (Density)
        text_len = len(text_for_filtering.replace(" ", ""))
        if text_len > 0:
            detected_words_len = sum(len(item['word']) for item in detected_words)
            density = detected_words_len / text_len
            if density > 0.4:
                total_score += self.weights['DENSITY_BONUS']

        # (C) 연속성 (Consecutive Degree)
        # "__B__" 또는 "__F__" 토큰이 2개 이상 연속으로 나오는 시퀀스 탐색
        sequences = re.findall(r'(?:__[BF]__\s*){2,}', text_for_filtering)
        
        consecutive_score = 0.0
        for seq in sequences:
            # 발견된 시퀀스 안에서 토큰(__F__, __B__) 수 계산
            seq_len = len(re.findall(r'__[BF]__', seq))
            if seq_len >= 2:
                consecutive_score += min(self.weights['CONSECUTIVE_BONUS'] * (seq_len - 1), self.weights['CONSECUTIVE_LEN_MAX'])
        
        total_score += min(consecutive_score, self.weights['CONSECUTIVE_MAX'])

        # 4. 최종 마무리
        return min(round(total_score, 2), 1.0)
    
if __name__ == "__main__":
    print("==========================================")
    print("▶ [Debug] RiskScorer 독립 실행 테스트")
    print("==========================================")

    scorer = RiskScorer()

    # 테스트 케이스: 1차 필터가 넘겨줄 법한 데이터들을 가상으로 만듦
    test_cases = [
        {
            "desc": "정상 문장 (감지된 것 없음)",
            "input": {
                "detected_words": [],
                "text_for_filtering": "안녕하세요 반갑습니다"
            }
        },
        {
            "desc": "약한 욕설 1개 (시스템 키워드)",
            "input": {
                "detected_words": [{'word': '바보', 'type': 'SYSTEM_KEYWORD'}],
                "text_for_filtering": "너 진짜 __F__ 구나"
            }
        },
        {
            "desc": "사용자 차단 단어 포함 (블랙리스트)",
            "input": {
                "detected_words": [{'word': '광고', 'type': 'USER_BLACKLIST'}],
                "text_for_filtering": "이거 __B__ 입니다 사세요"
            }
        },
        {
            "desc": "욕설 도배 (연속성/밀도/개수 모두 높음)",
            "input": {
                "detected_words": [
                    {'word': '씨발', 'type': 'SYSTEM_KEYWORD'},
                    {'word': '개새끼', 'type': 'SYSTEM_KEYWORD'},
                    {'word': '병신', 'type': 'SYSTEM_KEYWORD'}
                ],
                "text_for_filtering": "__F__ __F__ 너는 진짜 __F__ 이야"
            }
        }
    ]

    for case in test_cases:
        print(f"\n[Scenario]: {case['desc']}")
        
        # 점수 계산 실행
        score = scorer.execute(case['input'])
        
        print(f"  ㄴ Input Data: {case['input']['detected_words']}")
        print(f"  ㄴ Text Context: \"{case['input']['text_for_filtering']}\"")
        print(f"  ㄴ 🛡️ Risk Score: {score} / 1.0")
        
        if score >= 0.6:
            print("  => 🔴 [High Risk] 차단 가능성 높음")
        else:
            print("  => 🟢 [Low Risk] 안전함")
        print("-" * 40)