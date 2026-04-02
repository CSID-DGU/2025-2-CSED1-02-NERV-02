from app.repositories.dictionary import DictionaryRepository
from app.schemas.enums import ListType

class DictionaryService:
    def __init__(self, repo: DictionaryRepository):
        self.repo = repo
    
    async def get_user_dictionaries(self, user_id: int) -> dict:
        dicts = await self.repo.load_dictionaries(user_id)
        return {
            "whitelist": sorted(list(dicts.whitelist)),
            "blacklist": sorted(list(dicts.blacklist))
        }
    
    async def add_user_words(self, user_id: int, words: list[str], list_type: ListType) -> int:
        cleaned_words = {word.strip().lower() for word in words if word.strip()}
        return await self.repo.add_words(user_id, cleaned_words, list_type.value)
    
    async def remove_user_words(self, user_id: int, words: list[str], list_type: ListType) -> int:
        cleaned_words = {word.strip().lower() for word in words if word.strip()}
        return await self.repo.delete_words(user_id, cleaned_words, list_type.value)