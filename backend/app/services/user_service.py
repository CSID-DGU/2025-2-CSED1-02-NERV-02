import logging
from fastapi import HTTPException
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def get_settings(self, user_id: int):
        user = await self.repo.get_user_settings(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"유저 ID {user_id}를 찾을 수 없습니다.")
        return user

    async def update_settings(self, user_id: int, data: dict):
        user = await self.repo.get_user_settings(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"유저 ID {user_id}를 찾을 수 없습니다.")
        await self.repo.update_settings(user, data)
        return user
