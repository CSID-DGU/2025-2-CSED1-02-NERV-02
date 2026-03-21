import logging
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import UserDictionary, SystemDictionary

logger = logging.getLogger(__name__)

class DictionaryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def load_system_dict(self) -> set:
        try:
            stmt = select(SystemDictionary.word)
            result = await self.session.execute(stmt)
            system_dict = set(result.scalars().all())
            logger.info(f"[DictionaryRepository] 시스템 사전 로드 완료: {len(system_dict)}개 단어")
            return system_dict
        except Exception as e:
            logger.error(f"[DictionaryRepository] 시스템 사전 로드 실패: {e}")
            return set()

    async def load_user_dict(self, user_id: int) -> tuple[set, set]:
        try:
            stmt = select(UserDictionary.word, UserDictionary.list_type).where(UserDictionary.user_id == user_id)
            result = await self.session.execute(stmt)
            
            records = result.all()

            whitelist = {word for word, l_type in records if l_type == 'WHITELIST'}
            blacklist = {word for word, l_type in records if l_type == 'BLACKLIST'}
            
            logger.info(f"[DictionaryRepository] 유저({user_id}) 사전 로드 완료: 화이트({len(whitelist)}), 블랙({len(blacklist)})")
            return whitelist, blacklist
            
        except Exception as e:
            logger.error(f"[DictionaryRepository] 유저({user_id}) 사전 로드 실패: {e}")
            return set(), set()

    async def add_user_word(self, user_id: int, word: str, list_type: str) -> bool:
        try:
            new_word = UserDictionary(user_id=user_id, word=word, list_type=list_type)
            self.session.add(new_word)
            await self.session.commit()
            logger.info(f"[DictionaryRepository] 유저({user_id}) 사전 단어 추가: {word} ({list_type})")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"[DictionaryRepository] 유저({user_id}) 사전 단어 추가 실패: {e}")
            return False

    async def remove_user_word(self, user_id: int, word: str) -> bool:
        try:
            stmt = delete(UserDictionary).where(
                UserDictionary.user_id == user_id, 
                UserDictionary.word == word
            )
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info(f"[DictionaryRepository] 유저({user_id}) 사전 단어 삭제: {word}")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"[DictionaryRepository] 유저({user_id}) 사전 단어 삭제 실패: {e}")
            return False