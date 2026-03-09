import os
import json
import re
import time
from konlpy.tag import Okt
import ahocorasick

# ==========================================
# 1. Base Class (공통 로직 분리)
# ==========================================
class BaseFilter:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.dict_dir = os.path.join(self.base_dir, 'resources', 'dictionaries')
        
        self.user_dict_path = os.path.join(self.dict_dir, 'user_dictionary.json')
        self.system_dict_path = os.path.join(self.dict_dir, 'word_dictionary.json')
        
        self.user_whitelist = set()
        self.user_blacklist = set()
        self.system_dictionary = set()
        
        self._load_user_dictionary()
        self._load_system_dictionary()

    def _load_user_dictionary(self):
        try:
            with open(self.user_dict_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.user_whitelist = set(w.strip().lower() for w in data.get("user_whitelist", []))
            self.user_blacklist = set(w.strip().lower() for w in data.get("user_blacklist", []))
        except Exception:
            # 테스트를 위해 파일이 없으면 더미 데이터 삽입
            self.user_whitelist.update(["착한말", "좋은글"])
            self.user_blacklist.update(["바보", "멍청이", "악플"])

    def _load_system_dictionary(self):
        try:
            with open(self.system_dict_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for category, content in data.items():
                    for word in content.get("words", []):
                        self.system_dictionary.add(word.strip().lower())
        except Exception:
            # 테스트를 위해 파일이 없으면 더미 데이터 삽입
            self.system_dictionary.update(["도박", "광고", "불법사이트"])

    def normalize_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', '', text)
        return text

    def execute(self, original_text: str) -> dict:
        raise NotImplementedError("하위 클래스에서 구현해야 합니다.")


# ==========================================
# 2. Legacy: KoNLPy (Okt) 기반 필터
# ==========================================
class OktFirstPassFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.okt = Okt()

    def execute(self, original_text: str) -> dict:
        status = "PASSED"
        normalized_text = self.normalize_text(original_text)
        tokened_text = self.okt.pos(normalized_text)
        
        text_for_filtering = normalized_text
        detected_words = []

        for word, pos in tokened_text:
            word_lower = word.lower()

            if word_lower in self.user_whitelist:
                text_for_filtering = text_for_filtering.replace(word, "__W__")
                continue

            if word_lower in self.user_blacklist:
                detected_words.append({'word': word, 'type': 'USER_BLACKLIST'})
                text_for_filtering = text_for_filtering.replace(word, "__B__")
                continue
            
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


# ==========================================
# 3. New: Aho-Corasick 기반 필터 (권장)
# ==========================================
class AhoCorasickFirstPassFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.automaton = ahocorasick.Automaton()
        self._build_automaton()

    def _build_automaton(self):
        """
        사전에 있는 모든 단어를 트라이(Trie) 구조의 오토마톤에 등록합니다.
        """
        for w in self.user_whitelist:
            self.automaton.add_word(w, (w, 'WHITELIST'))
        for w in self.user_blacklist:
            self.automaton.add_word(w, (w, 'USER_BLACKLIST'))
        for w in self.system_dictionary:
            self.automaton.add_word(w, (w, 'SYSTEM_KEYWORD'))
        
        # 오토마톤 빌드 (이 작업은 초기 1회만 수행되므로 매우 효율적입니다)
        self.automaton.make_automaton()

    def execute(self, original_text: str) -> dict:
        status = "PASSED"
        normalized_text = self.normalize_text(original_text)
        text_for_filtering = normalized_text
        detected_words = []
        
        # 매칭된 단어 찾기 (한 번의 스캔으로 모든 키워드 탐색 O(N))
        matches = []
        for end_idx, (word, w_type) in self.automaton.iter(normalized_text):
            matches.append((word, w_type))
            
        # 중복 제거 (replace 시 문제가 없도록)
        seen = set()
        unique_matches = []
        for word, w_type in matches:
            if word not in seen:
                seen.add(word)
                unique_matches.append((word, w_type))

        # 발견된 단어들에 대해 처리
        for word, w_type in unique_matches:
            if w_type == 'WHITELIST':
                text_for_filtering = text_for_filtering.replace(word, "__W__")
            elif w_type == 'USER_BLACKLIST':
                detected_words.append({'word': word, 'type': 'USER_BLACKLIST'})
                text_for_filtering = text_for_filtering.replace(word, "__B__")
            elif w_type == 'SYSTEM_KEYWORD':
                detected_words.append({'word': word, 'type': 'SYSTEM_KEYWORD'})
                text_for_filtering = text_for_filtering.replace(word, "__F__")

        if detected_words:
            status = 'FILTERED_BY_FIRST_PASS'
            
        return {
            'original_text': original_text,
            'status': status,
            'detected_words': detected_words,
            'text_for_filtering': text_for_filtering
        }


# ==========================================
# 4. 성능 비교 벤치마크 (Benchmark)
# ==========================================
def run_benchmark():
    print("==========================================")
    print("▶ [Benchmark] FirstPassFilter 성능 비교")
    print("==========================================")

    print("\n[1] 리소스 로딩 및 초기화...")
    okt_filter = OktFirstPassFilter()
    aho_filter = AhoCorasickFirstPassFilter()

    # 테스트 데이터 (1000개의 문장으로 증폭)
    base_sentences = [
        "이 영상 정말 유익하고 좋네요! 좋은글 감사합니다.",
        "진짜 바보 멍청이 같은 놈들, 악플 달지 마라.",
        "불법사이트 도박 광고 신고합니다.",
        "오늘 날씨가 참 좋습니다. 다들 행복하세요.",
        "아무 의미 없는 평범한 더미 데이터입니다."
    ]
    test_comments = base_sentences * 200  # 총 1000문장
    print(f"[2] 테스트 데이터 준비 완료: 총 {len(test_comments)} 문장")

    # --- Okt 테스트 ---
    print("\n[3] KoNLPy (Okt) 테스트 시작...")
    okt_filter.execute("워밍업") # 첫 실행 지연 방지
    start_time = time.perf_counter()
    for comment in test_comments:
        okt_filter.execute(comment)
    okt_time = time.perf_counter() - start_time
    print(f"  ㄴ 전체 소요 시간: {okt_time:.4f} sec")
    print(f"  ㄴ 문장당 평균 속도: {(okt_time/len(test_comments))*1000:.4f} ms")

    # --- Aho-Corasick 테스트 ---
    print("\n[4] Aho-Corasick 테스트 시작...")
    start_time = time.perf_counter()
    for comment in test_comments:
        aho_filter.execute(comment)
    aho_time = time.perf_counter() - start_time
    print(f"  ㄴ 전체 소요 시간: {aho_time:.4f} sec")
    print(f"  ㄴ 문장당 평균 속도: {(aho_time/len(test_comments))*1000:.4f} ms")

    print("\n==========================================")
    print(f"▶ [결과] Aho-Corasick이 Okt 대비 약 {okt_time / aho_time:.1f}배 빠릅니다!")
    print("==========================================")

if __name__ == "__main__":
    run_benchmark()