import re
import hashlib
import logging
import ahocorasick

from app.schemas.enums import FilterStatus, WordType

logger = logging.getLogger(__name__)

class FirstPassFilter:
    def __init__(self):
        self._cache: dict[str, ahocorasick.Automaton] = {}

    _MAX_CACHE_SIZE = 100

    @staticmethod
    def _compute_hash(whitelist: set, blacklist: set, system_dict: set) -> str:
        all_words = sorted(whitelist) + sorted(blacklist) + sorted(system_dict)
        return hashlib.md5("|".join(all_words).encode()).hexdigest()

    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r'[^가-힣a-zA-Z0-9\s]', '', text.lower())

    @staticmethod   
    def _build_automaton(whitelist: set, blacklist: set, system_dict: set) -> ahocorasick.Automaton:
        new_automaton = ahocorasick.Automaton()
        for w in whitelist: new_automaton.add_word(w, (w, WordType.WHITELIST))
        for w in blacklist: new_automaton.add_word(w, (w, WordType.USER_BLACKLIST))
        for w in system_dict: new_automaton.add_word(w, (w, WordType.SYSTEM_KEYWORD))
        if len(new_automaton) > 0: new_automaton.make_automaton()
        return new_automaton

    def execute(self, original_text: str, whitelist: set, blacklist: set, system_dict: set) -> dict:
        cache_key = self._compute_hash(whitelist, blacklist, system_dict)
        if cache_key not in self._cache:
            if len(self._cache) >= self._MAX_CACHE_SIZE:
                self._cache.clear()
            self._cache[cache_key] = self._build_automaton(whitelist, blacklist, system_dict)
        automaton = self._cache[cache_key]
        
        status = FilterStatus.PASSED
        normalized_text = self.normalize_text(original_text)
        masked_text = normalized_text
        detected_words = []
        
        matches = []
        if len(automaton) > 0:
            for _, (word, wordtype) in automaton.iter(normalized_text):
                matches.append((word, wordtype))
            
        seen = set()
        unique_matches = []
        for word, wordtype in matches:
            if word not in seen:
                seen.add(word)
                unique_matches.append((word, wordtype))

        unique_matches.sort(key=lambda x: (0 if x[1] == WordType.WHITELIST else 1, -len(x[0])))

        for word, wordtype in unique_matches:
            if word not in masked_text: continue
                
            if wordtype == WordType.WHITELIST:
                masked_text = masked_text.replace(word, "__W__")
            elif wordtype == WordType.USER_BLACKLIST:
                detected_words.append({'word': word, 'type': WordType.USER_BLACKLIST})
                masked_text = masked_text.replace(word, "__B__")
            elif wordtype == WordType.SYSTEM_KEYWORD:
                detected_words.append({'word': word, 'type': WordType.SYSTEM_KEYWORD})
                masked_text = masked_text.replace(word, "__F__")

        if detected_words:
            status = FilterStatus.FILTERED_BY_FIRST_PASS
            
        return {
            'original_text': original_text,
            'status': status,
            'detected_words': detected_words,
            'masked_text': masked_text
        }