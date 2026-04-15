import logging
from dataclasses import dataclass
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import UserDictionary

logger = logging.getLogger(__name__)

@dataclass
class FilterDictionaries:
    whitelist: set[str]
    blacklist: set[str]
    system_dict: set[str]

class DictionaryRepository:
    def __init__(self, session: AsyncSession, system_dict: set[str]):
        self.session = session
        self.system_dict = system_dict

    async def _load_user_dict(self, user_id: int) -> tuple[set, set]:
        stmt = select(UserDictionary.word, UserDictionary.list_type).where(UserDictionary.user_id == user_id)
        result = await self.session.execute(stmt)
        records = result.all()
        whitelist = {word for word, l_type in records if l_type == 'WHITELIST'}
        blacklist = {word for word, l_type in records if l_type == 'BLACKLIST'}
        logger.info(f"[DictionaryRepository] 유저({user_id}) 사전 로드 완료")
        return whitelist, blacklist

    async def load_dictionaries(self, user_id: int) -> FilterDictionaries:
        whitelist, blacklist = await self._load_user_dict(user_id)
        return FilterDictionaries(whitelist=whitelist, blacklist=blacklist, system_dict=self.system_dict)

    async def add_words(self, user_id: int, words: set[str], list_type: str) -> int:
        if not words:
            return 0
        self.session.add_all([
            UserDictionary(user_id=user_id, word=word, list_type=list_type)
            for word in words
        ])
        await self.session.commit()
        logger.info(f"[DictionaryRepository] 유저({user_id}) {list_type} 추가: {', '.join(sorted(words))}")
        return len(words)

    async def delete_words(self, user_id: int, words: set[str], list_type: str) -> int:
        if not words:
            return 0
        stmt = delete(UserDictionary).where(
            UserDictionary.user_id == user_id,
            UserDictionary.word.in_(words)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.info(f"[DictionaryRepository] 유저({user_id}) {list_type} 삭제: {', '.join(sorted(words))}")
        return len(words)
