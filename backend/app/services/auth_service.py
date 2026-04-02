from datetime import timedelta
from fastapi import HTTPException, status

from app.core.security import create_access_token
from app.core.config import settings
from app.repositories.user import UserRepository
from app.schemas import Token


class AuthService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def _create_token(self, user) -> Token:
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return Token(access_token=access_token, token_type="bearer", user_id=user.id)

    async def register(self, username: str, password: str) -> Token:
        existing_user = await self.repo.get_user_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 사용자명입니다."
            )

        user = await self.repo.create_user_with_password(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="사용자 생성에 실패했습니다."
            )

        return self._create_token(user)

    async def login(self, username: str, password: str) -> Token:
        user = await self.repo.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자명 또는 비밀번호가 올바르지 않습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._create_token(user)
