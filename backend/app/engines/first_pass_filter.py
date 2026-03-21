import re
import logging
import ahocorasick
from typing import List, Dict, Set, Tuple
from app.core.config import settings
from app.repositories.dictionary_repository import DictionaryRepository

logger = logging.getLogger(__name__)

class FirstPassFilter:
    def __init__(self, repo: DictionaryRepository):
        self.dict_repo = repo
        self.automaton = ahocorasick.Automaton()
      
    async def reload_engine(self, user_id: int):

        logger.info(f"[FirstPassFilter] 유저({user_id}) 전용 엔진 조립 시작...")
        
        user_whitelist, user_blacklist = await self.dict_repo.load_user_dict(user_id)
        system_dictionary = await self.dict_repo.load_system_dict()
        
        new_automaton = ahocorasick.Automaton()
        
        for w in user_whitelist: 
            new_automaton.add_word(w, (w, 'WHITELIST'))
        for w in user_blacklist: 
            new_automaton.add_word(w, (w, 'USER_BLACKLIST'))
        for w in system_dictionary: 
            new_automaton.add_word(w, (w, 'SYSTEM_KEYWORD'))
        
        if len(new_automaton) > 0:
            new_automaton.make_automaton()
            self.automaton = new_automaton
            logger.info(f"유저({user_id}) 엔진 조립 완료 (총 {len(new_automaton)}개 단어)")
        else:
            logger.warning(f"유저({user_id})의 사전 데이터가 비어있습니다.")

    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r'[^가-힣a-zA-Z0-9\s]', '', text.lower())

    def execute(self, original_text: str) -> dict:
        status = "PASSED"
        normalized_text = self.normalize_text(original_text)
        masked_text = normalized_text
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

        unique_matches.sort(key=lambda x: (0 if x[1] == 'WHITELIST' else 1, -len(x[0])))

        for word, w_type in unique_matches:
            if word not in masked_text: continue
                
            if w_type == 'WHITELIST':
                masked_text = masked_text.replace(word, "__W__")
            elif w_type == 'USER_BLACKLIST':
                detected_words.append({'word': word, 'type': 'USER_BLACKLIST'})
                masked_text = masked_text.replace(word, "__B__")
            elif w_type == 'SYSTEM_KEYWORD':
                detected_words.append({'word': word, 'type': 'SYSTEM_KEYWORD'})
                masked_text = masked_text.replace(word, "__F__")

        if detected_words:
            status = 'FILTERED_BY_FIRST_PASS'
            
        return {
            'original_text': original_text,
            'status': status,
            'detected_words': detected_words,
            'masked_text': masked_text
        }