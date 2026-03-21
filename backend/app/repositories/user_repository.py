import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_settings(self, user_id: int) -> User | None:
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"[UserRepository] 유저 ID {user_id}를 찾을 수 없습니다.")
            
            return user
        except Exception as e:
            logger.error(f"[UserRepository] 유저 설정 조회 중 오류 발생: {e}")
            return None

    async def create_user(self, username: str, **kwargs) -> User | None:
        try:
            new_user = User(username=username, **kwargs)
            self.session.add(new_user)
            await self.session.commit()
            await self.session.refresh(new_user) # 생성된 ID 등을 다시 불러옴
            return new_user
        except Exception as e:
            await self.session.rollback()
            logger.error(f"[UserRepository] 유저 생성 실패: {e}")
            return None