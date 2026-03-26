import logging
from enum import Enum
from app.repositories.dictionary import DictionaryRepository

logger = logging.getLogger(__name__)

class ListType(str, Enum):
    WHITELIST = "whitelist"
    BLACKLIST = "blacklist"

class DictionaryService:
    def __init__(self, repo: DictionaryRepository):
        self.repo = repo
    
    async def get_user_dictionaries(self, user_id: int) -> dict:
        whitelist, blacklist = await self.repo.load_user_dict(user_id)
        return {
            "whitelist": sorted(list(whitelist)),
            "blacklist": sorted(list(blacklist))
        }
    
    async def add_user_words(self, user_id: int, words: list[str], list_type: ListType) -> int:
        db_list_type = list_type.value.upper()
        added_count = 0
        
        cleaned_words = {word.strip().lower() for word in words if word.strip()}
        
        for word in cleaned_words:
            if await self.repo.add_user_word(user_id, word, db_list_type):
                added_count += 1
        
        if added_count > 0:
            logger.info(f"[DictionaryService] 유저({user_id})의 '{db_list_type}'에 {added_count}개 단어 추가 완료.")
        
        return added_count
    
    async def remove_user_words(self, user_id: int, words: list[str]) -> int:
        removed_count = 0
        
        cleaned_words = {word.strip().lower() for word in words if word.strip()}
        
        for word in cleaned_words:
            if await self.repo.remove_user_word(user_id, word):
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"[DictionaryService] 유저({user_id})의 사전에서 {removed_count}개 단어 삭제 완료.")
        
        return removed_count