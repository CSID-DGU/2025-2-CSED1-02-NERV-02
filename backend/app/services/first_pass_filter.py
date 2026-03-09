import os
import json
import re
from konlpy.tag import Okt

class FirstPassFilter:
    def __init__(self):
        print("[System] 1차 필터 리소스 로딩 시작...")
        
        # 1. 형태소 분석기 초기화 (메모리 로드)
        self.okt = Okt()
        
        # 2. 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)
        self.dict_dir = os.path.join(app_dir, 'resources', 'dictionaries')
        
        self.user_dict_path = os.path.join(self.dict_dir, 'user_dictionary.json')
        self.system_dict_path = os.path.join(self.dict_dir, 'word_dictionary.json')
        
        # 3. 데이터 컨테이너 초기화
        self.user_whitelist = set()
        self.user_blacklist = set()
        self.system_dictionary = set()
        
        # 4. 로드
        self._load_user_dictionary()
        self._load_system_dictionary()
        
        print("[System] 1차 필터 준비 완료.")

    def get_user_dictionary(self, list_type: str) -> dict:
        """
        현재 메모리에 로드된 사용자 사전을 반환합니다.
        """

        if list_type == 'whitelist':
            return {"whitelist": sorted(list(self.user_whitelist))}
        
        elif list_type == 'blacklist':
            return {"blacklist": sorted(list(self.user_blacklist))}
        
        return {}

    def _update_user_dictionary(self, words: list, list_type: str, action: str) -> int:
        """
        사용자 사전을 갱신(추가/삭제)하고 파일에 저장합니다.
        """
        if list_type == 'whitelist':
            target_set = self.user_whitelist
        elif list_type == 'blacklist':
            target_set = self.user_blacklist
        else:
            return 0

        changed_count = 0
        
        for word in words:
            word = word.strip().lower()
            if not word: continue

            if action == 'add':
                if word not in target_set:
                    target_set.add(word)
                    changed_count += 1
                    
            elif action == 'remove':
                if word in target_set:
                    target_set.remove(word)
                    changed_count += 1
        
        if changed_count > 0:
            self._save_user_dictionary()
            
        return changed_count

    def _save_user_dictionary(self) -> bool:
        """
        현재 메모리의 화이트/블랙리스트를 파일에 덮어씁니다.
        """
        try:
            data = {
                "user_whitelist": sorted(list(self.user_whitelist)),
                "user_blacklist": sorted(list(self.user_blacklist))
            }
            with open(self.user_dict_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Error] 사용자 사전 저장 실패: {e}")
            return False

    def _load_user_dictionary(self):
        """사용자 사전 로드 """
        try:
            with open(self.user_dict_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.user_whitelist = set(w.strip().lower() for w in data.get("user_whitelist", []))
            self.user_blacklist = set(w.strip().lower() for w in data.get("user_blacklist", []))
            
            print(f"  ㄴ 사용자 사전 로드됨: 화이트({len(self.user_whitelist)}), 블랙({len(self.user_blacklist)})")
            
        except Exception as e: print(f"  [Error] 사용자 사전 로드 실패: {e}")           

    def _load_system_dictionary(self):
        """시스템 사전 로드 """
        try:
            with open(self.system_dict_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for category, content in data.items():
                    for word in content.get("words", []):
                        self.system_dictionary.add(word.strip().lower())
            
            print(f"  ㄴ 시스템 사전 로드됨: {len(self.system_dictionary)}개 단어")

        except Exception as e: print(f"  [Error] 시스템 사전 로드 실패: {e}")

    def normalize_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', '', text)
        return text

    def execute(self, original_text: str) -> dict:
        """외부에서 호출하는 메인 메서드"""
        status = "PASSED"
        
        # 1. 정규화
        normalized_text = self.normalize_text(original_text)
        
        # 2. 형태소 분석 (self.okt 사용)
        tokened_text = self.okt.pos(normalized_text)
        
        text_for_filtering = normalized_text
        detected_words = []

        for word, pos in tokened_text:
            word_lower = word.lower() # 혹시 몰라 한 번 더 소문자 처리

            # [A] 화이트리스트
            if word_lower in self.user_whitelist:
                text_for_filtering = text_for_filtering.replace(word, "__W__")
                continue

            # [B] 블랙리스트
            if word_lower in self.user_blacklist:
                detected_words.append({'word': word, 'type': 'USER_BLACKLIST'})
                text_for_filtering = text_for_filtering.replace(word, "__B__")
                continue
            
            # [C] 시스템 사전
            if word_lower in self.system_dictionary:
                detected_words.append({'word': word, 'type': 'SYSTEM_KEYWORD'})
                text_for_filtering = text_for_filtering.replace(word, "__F__")
                continue

        if detected_words:
            status = 'FILTERED_BY_FIRST_PASS'
        
        return {
            'original_text': original_text,
            'status': status,
            'detected_words': detected_words,
            'text_for_filtering': text_for_filtering
        }

if __name__ == "__main__":
    import json
    import time
    import os

    print("==========================================")
    print("▶ [Debug] FirstPassFilter 독립 실행 테스트")
    print("==========================================")

    # 1. 클래스 인스턴스 생성 (이때 사전 로드됨)
    filter_instance = FirstPassFilter()
    
    # 2. 테스트 케이스
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(current_dir)
    test_file_path = os.path.join(app_dir, 'resources', 'test_data', 'test_comments.txt')
    
    with open(test_file_path, "r", encoding="utf-8") as f:
        test_comments = [line.strip() for line in f if line.strip()]
    
    # 3. 테스트 실행
    filter_instance.execute("더미 데이터")
    total_time = 0
    for idx, comment in enumerate(test_comments):
        start = time.perf_counter()
        result = filter_instance.execute(comment)
        end = time.perf_counter()
        # print(f"\n[Input] : {comment}")
        
        # # 결과 출력 (JSON 형태로 예쁘게)
        # print("[Result]:")
        # print(json.dumps(result, indent=4, ensure_ascii=False))
        print(f"[Time]: {(end - start)*1000:.4f} ms")
        # print("-" * 40)
        total_time += (end - start)

    avg_time = total_time*1000 / len(test_comments)

    print(f"▶ 테스트 케이스 수: {len(test_comments)}")
    print(f"▶ 전체 소요 시간: {total_time:.4f} sec")
    print(f"▶ 문장당 평균 처리 속도: {avg_time:.4f} ms")