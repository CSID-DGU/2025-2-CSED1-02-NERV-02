import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from app.core.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_settings(self, user: User, data: dict) -> None:
        for field, value in data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        await self.session.commit()

    async def get_user_settings(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"[UserRepository] 유저 ID {user_id}를 찾을 수 없습니다.")
        return user

    async def create_user(self, username: str, **kwargs) -> User:
        new_user = User(username=username, **kwargs)
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user

    async def get_user_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user_with_password(self, username: str, password: str) -> User:
        loop = asyncio.get_running_loop()
        hashed_password = await loop.run_in_executor(None, get_password_hash, password)
        new_user = User(
            username=username,
            password_hash=hashed_password,
            is_active=True,
        )
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        logger.info(f"[UserRepository] 새 유저 생성 완료: {username} (ID: {new_user.id})")
        return new_user

    async def authenticate_user(self, username: str, password: str) -> User | None:
        user = await self.get_user_by_username(username)
        if not user:
            logger.warning(f"[UserRepository] 인증 실패: 존재하지 않는 사용자 '{username}'")
            return None

        loop = asyncio.get_running_loop()
        is_valid = await loop.run_in_executor(None, verify_password, password, user.password_hash)
        if not is_valid:
            logger.warning(f"[UserRepository] 인증 실패: 비밀번호 불일치 '{username}'")
            return None

        logger.info(f"[UserRepository] 인증 성공: {username} (ID: {user.id})")
        return user
