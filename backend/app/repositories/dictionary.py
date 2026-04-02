import logging
from dataclasses import dataclass
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import UserDictionary, SystemDictionary

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
        try:
            stmt = select(UserDictionary.word, UserDictionary.list_type).where(UserDictionary.user_id == user_id)
            result = await self.session.execute(stmt)
            records = result.all()
            whitelist = {word for word, l_type in records if l_type == 'WHITELIST'}
            blacklist = {word for word, l_type in records if l_type == 'BLACKLIST'}
            logger.info(f"[DictionaryRepository] 유저({user_id}) 사전 로드 완료")
            return whitelist, blacklist
        except Exception as e:
            logger.error(f"[DictionaryRepository] 유저({user_id}) 사전 로드 실패: {e}")
            return set(), set()
    
    async def load_dictionaries(self, user_id: int) -> FilterDictionaries:
        whitelist, blacklist = await self._load_user_dict(user_id)
        return FilterDictionaries(whitelist=whitelist, blacklist=blacklist, system_dict=self.system_dict)

    async def add_words(self, user_id: int, words: set[str], list_type: str) -> int:
        if not words:
            return 0
        try:
            self.session.add_all([
                UserDictionary(user_id=user_id, word=word, list_type=list_type)
                for word in words
            ])
            await self.session.commit()
            logger.info(f"[DictionaryRepository] 유저({user_id}) {list_type} 추가: {', '.join(sorted(words))}")
            return len(words)
        except Exception as e:
            await self.session.rollback()
            logger.error(f"[DictionaryRepository] 유저({user_id}) {list_type} 추가 실패: {e}")
            return 0

    async def delete_words(self, user_id: int, words: set[str], list_type: str) -> int:
        if not words:
            return 0
        try:
            stmt = delete(UserDictionary).where(
                UserDictionary.user_id == user_id,
                UserDictionary.word.in_(words)
            )
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info(f"[DictionaryRepository] 유저({user_id}) {list_type} 삭제: {', '.join(sorted(words))}")
            return len(words)
        except Exception as e:
            await self.session.rollback()
            logger.error(f"[DictionaryRepository] 유저({user_id}) {list_type} 삭제 실패: {e}")
            return 0
        
async def load_system_dict(session: AsyncSession) -> set[str]:
    try:
        result = await session.execute(select(SystemDictionary.word))
        system_dict = set(result.scalars().all())
        logger.info(f"[DictionaryRepository] 시스템 사전 로드 완료: {len(system_dict)}개 단어")
        return system_dict
    except Exception as e:
        logger.error(f"[DictionaryRepository] 시스템 사전 로드 실패: {e}")
        return set()