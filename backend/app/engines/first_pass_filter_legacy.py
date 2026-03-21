import re
import logging
from konlpy.tag import Okt
from app.repositories.dictionary_repository import DictionaryRepository

logger = logging.getLogger(__name__)

class LegacyFirstPassFilter:
    def __init__(self, repo: DictionaryRepository):
        self.dict_repo = repo
        
        logger.info("[LegacyFirstPassFilter] 형태소 분석기(Okt) 로드 중... (시간이 조금 걸릴 수 있습니다)")
        self.okt = Okt()
        
        self.user_whitelist = set()
        self.user_blacklist = set()
        self.system_dictionary = set()

    async def reload_engine(self, user_id: int):
        """사전 데이터를 다시 불러와서 최신 상태로 갱신합니다."""
        logger.info(f"[LegacyFirstPassFilter] 유저({user_id}) 사전 데이터 Reload ...")
        
        self.user_whitelist, self.user_blacklist = await self.dict_repo.load_user_dict(user_id)
        self.system_dictionary = await self.dict_repo.load_system_dict()
        
        logger.info(f"[LegacyFirstPassFilter] 유저({user_id}) 사전 갱신 완료 (W:{len(self.user_whitelist)}, B:{len(self.user_blacklist)}, S:{len(self.system_dictionary)})")

    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r'[^가-힣a-zA-Z0-9\s]', '', text.lower())
    
    def execute(self, original_text: str) -> dict:
        status = "PASSED"
        normalized_text = self.normalize_text(original_text)
        
        # Okt 형태소 분석
        tokened_text = self.okt.pos(normalized_text)
        
        text_for_filtering = normalized_text
        detected_words = []

        for word, pos in tokened_text:
            word_lower = word.lower()

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