# app/services/first_pass_filter.py
import re
import logging
import ahocorasick
from app.repositories.dictionary_repository import DictionaryRepository

logger = logging.getLogger(__name__)

class FirstPassFilterV2:
    def __init__(self, repo: DictionaryRepository):
        self.dict_repo = repo
        self.automaton = ahocorasick.Automaton()
        self.reload_engine() # 🚨 초기화할 때 엔진 조립!

    def reload_engine(self):
        """사전 데이터를 다시 불러와서 엔진을 최신 상태로 갱신합니다."""
        logger.info("[FirstPassFilter] 아호-코라식 엔진 조립(Reload) 시작...")
        user_whitelist, user_blacklist = self.dict_repo.load_user_dict()
        system_dictionary = self.dict_repo.load_system_dict()
        
        self.automaton = ahocorasick.Automaton()
        for w in user_whitelist: self.automaton.add_word(w, (w, 'WHITELIST'))
        for w in user_blacklist: self.automaton.add_word(w, (w, 'USER_BLACKLIST'))
        for w in system_dictionary: self.automaton.add_word(w, (w, 'SYSTEM_KEYWORD'))
        
        if len(self.automaton) > 0:
            self.automaton.make_automaton()

    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r'[^가-힣a-zA-Z0-9\s]', '', text.lower())

    def execute(self, original_text: str) -> dict:
        status = "PASSED"
        normalized_text = self.normalize_text(original_text)
        text_for_filtering = normalized_text
        detected_words = []
        
        matches = []
        if len(self.automaton) > 0:
            for end_idx, (word, w_type) in self.automaton.iter(normalized_text):
                matches.append((word, w_type))
            
        seen = set()
        unique_matches = []
        for word, w_type in matches:
            if word not in seen:
                seen.add(word)
                unique_matches.append((word, w_type))

        def sort_key(item):
            word, w_type = item
            type_priority = 0 if w_type == 'WHITELIST' else 1
            return (type_priority, -len(word))
        
        unique_matches.sort(key=sort_key)

        for word, w_type in unique_matches:
            if word not in text_for_filtering: continue
                
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