import json
import openai
import os
import torch
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from app.core.config import settings

class SecondPassFilter:
    def __init__(self, api_key=None):
        # 프롬프트 모듈 설정 로드
        self.basic_ai_module = settings.BASIC_AI_MODULE
        self.special_ai_modules = settings.SPECIAL_AI_MODULES
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)
        self.basic_module_dir = os.path.join(app_dir, "resources", "modules", "basic_ai_module")
        
        self.basic_threshold = settings.BASIC_THRESHOLD
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.basic_module_dir)
            self.basic_module = AutoModelForSequenceClassification.from_pretrained(self.basic_module_dir)
            self.basic_module.to(self.device)
            self.basic_module.eval()
        except Exception as e:
            print(f"[ERROR] BASIC 모듈 로드 실패: {e}")
            self.tokenizer = None
            self.basic_module_dir = None

        # OPEN AI 클라이언트 초기화
        api_key = settings.OPENAI_API_KEY
        
        if api_key:
            # 키가 있으면 정상적으로 클라이언트 생성
            self.client = openai.OpenAI(api_key=api_key)
        else:
            # 키가 없으면 클라이언트를 None으로 설정하고 경고 출력
            self.client = None
            print("[WARNING] OPENAI_API_KEY가 설정되지 않았습니다. 2차 필터링(AI)이 비활성화됩니다.")        

    def _tokenize_for_module(self, text: str):
        """ 
        [토큰화 담당] Basic 모듈에서의 처리를 위한 토큰화를 진행합니다.
        """
        if not text:
            return []

        # 마스킹 토큰을 공백으로 치환
        tmp = text
        for ph in ("__F__", "__B__", "__W__"):
            tmp = tmp.replace(ph, " ")

        raw_tokens = re.findall(r"[가-힣ㄱ-ㅎㅏ-ㅣA-Za-z0-9]+", tmp)

        tokens = []
        for w in raw_tokens:
            w = w.strip()
            if not w:
                continue

            if len(w) == 1 and not w.isdigit():
                continue
            
            if len(w) >= 10:
                continue
            tokens.append(w)

        return tokens
    
    def _call_basic_module(self, token: str) -> float:
        """
        [Basic 모듈 실행 담당] Basic 모듈을 이용하여 문장을 분석합니다.
        """
        if not self.basic_module or not self.tokenizer:
            return 0.0

        inputs = self.tokenizer(
            token,
            truncation=True,
            padding=False,
            max_length=64,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.basic_module(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)[0]
            return float(probs[1]) # 악성일 확률

    def _construct_prompt(self, text):
        """
        [프롬프트 생성 담당] 질문 텍스트를 만듭니다.
        """
        check_list = []
        for rule in self.basic_ai_module:
            check_list.append(f"- [기본검사] {rule}")
        for category, rule in self.special_ai_modules.items():
            check_list.append(f"- [{category}] {rule}")

        criteria = "\n".join(check_list)

        return f"""
        분석할 댓글: "{text}"
        
        [판단 기준]
        다음의 모든 기준을 적용하여 엄격하게 검사하세요:
        {criteria}
        
        위 댓글에서 위반되는 '구체적인 부분(단어, 구문)'을 모두 찾아내어 아래 JSON 형식으로 응답하세요.
        각 적발 항목에 대해 가장 적합한 모듈(Category)을 지정해야 합니다.
        
        {{
            "detected_items": [
                {{
                    "keyword": "문제된 단어/구문",
                    "category": "위반 모듈명 (예: PRIVACY, SEXUAL)"
                }}
            ],
            "reason": "판단 사유",
            "severity": integer (1~5)
        }}
        """

    def _call_openai_api(self, prompt):
        """
        [API 통신 담당] 실제 GPT에게 질문을 던지고 JSON 결과를 받아옵니다.
        """
        if self.client is None:
            # 빈 응답을 반환하여 2차 필터링 로직이 정상적으로 통과되게 함
            return {"detected_items": [], "reason": "API Key Missing", "severity": 0}

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo", # 또는 "gpt-4o-mini" (상위 모델)
                messages=[
                    {"role": "system", "content": "You are a strict content moderator. Output in JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}, # JSON 모드 강제 (중요)
                temperature=0.0 # 일관된 분석을 위해 0으로 설정
            )
            content = response.choices[0].message.content
            if not content:
                return {}
            return json.loads(content)
            
        except Exception as e:
            print(f"OpenAI API 호출 실패: {e}")
            return {} # 실패 시 빈 객체 반환하여 로직이 안 터지게 함

    def execute(self, first_pass_result):
        """
        메인 실행 함수
        """
        second_pass_result = first_pass_result

        try:
            # 1. Basic 모듈 처리
            if self.basic_module is not None:
                current_text = second_pass_result.get("text_for_filtering", "")
                tokens = self._tokenize_for_module(current_text)

                for word in tokens:
                    score = self._call_basic_module(word)
                    if score >= self.basic_threshold:
                        second_pass_result['status'] = "FILTERED_BY_SECOND_PASS"
                        second_pass_result["detected_words"].append({
                            "word": word,
                            "type": "AI_BASIC"
                        })
                        second_pass_result["text_for_filtering"] = second_pass_result["text_for_filtering"].replace(word, "__S__")

            # 2. 프롬프트 생성
            prompt_text = self._construct_prompt(second_pass_result.get('text_for_filtering', ''))
            
            # 3. API 호출
            gpt_response = self._call_openai_api(prompt_text)

            # 4. 결과 처리
            ai_detected_items = gpt_response.get('detected_items', [])
            
            if ai_detected_items:
                second_pass_result['status'] = "FILTERED_BY_SECOND_PASS"

                for item in ai_detected_items:
                    word = item.get('keyword', '')
                    category = item.get('category', 'DETECTED')
                    
                    if word:
                        # 리스트에 추가
                        second_pass_result['detected_words'].append({
                            "word": word,
                            "type": f"AI_{category.upper()}"
                        })
                        
                        # 텍스트 수정
                        second_pass_result['text_for_filtering'] = second_pass_result['text_for_filtering'].replace(word, "__S__")

            return second_pass_result

        except Exception as e:
            print(f"2차 필터 에러: {e}")
            return first_pass_result
        
        
if __name__ == "__main__":
    print("==========================================")
    print("▶ [Debug] 2차 필터링 독립 실행 테스트")
    print("==========================================")

    second_filter = SecondPassFilter()

    # 테스트 케이스
    test_cases = [
        {
            "desc": "정상 문장 (감지된 것 없음)",
            "input": {
                "detected_words": [],
                "text_for_filtering": "안녕하세요 반갑습니다"
            }
        },
        {
            "desc": "욕설 회피 (문자)",
            "input": {
                "detected_words": [{'word': '바보', 'type': 'SYSTEM_KEYWORD'}],
                "text_for_filtering": "너 진짜 느ㄱㄷㅈㅂ금마 병신 __F__ 구나"
            }
        },
        {
            "desc": "욕설 회피 (숫자)",
            "input": {
                "detected_words": [
                    {'word': '씨발', 'type': 'SYSTEM_KEYWORD'},
                    {'word': '개새끼', 'type': 'SYSTEM_KEYWORD'},
                    {'word': '병신', 'type': 'SYSTEM_KEYWORD'}
                ],
                "text_for_filtering": "씨1321발 __F__ __F__ 너는 진짜 __F__ 이야"
            }
        }
    ]

    for idx, case in enumerate(test_cases, start=1):
        print(f"\n[Scenario]: {case['desc']}")

        first_pass_result = {
            "status": "FILTERED_BY_FIRST_PASS",
            "detected_words": list(case["input"].get("detected_words", [])),  # 얕은 복사
            "text_for_filtering": case["input"].get("text_for_filtering", "")
        }
        print(f"  ㄴ Input Data: {case['input']['detected_words']}")
        print(f"  ㄴ Text Context: \"{case['input']['text_for_filtering']}\"")

        # 2차 필터 실행
        result = second_filter.execute(first_pass_result)

        print(f"  ㄴ Output Data: {result['detected_words']}")
        print(f"  ㄴ Output Text Context: {result['text_for_filtering']} ")
        print("\n" + "-" * 40)