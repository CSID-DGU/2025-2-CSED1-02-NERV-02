from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.repositories.user import UserRepository
from app.repositories.dictionary import DictionaryRepository
from app.repositories.video_analysis_cache_repository import VideoAnalysisCacheRepository
from app.repositories.comment_analysis_cache_repository import CommentAnalysisCacheRepository


def get_system_dict(request: Request) -> set[str]:
    return request.app.state.system_dict


async def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


async def get_dictionary_repository(
    session: AsyncSession = Depends(get_db),
    system_dict: set[str] = Depends(get_system_dict),
) -> DictionaryRepository:
    return DictionaryRepository(session, system_dict)


async def get_video_analysis_cache_repository(
    session: AsyncSession = Depends(get_db),
) -> VideoAnalysisCacheRepository:
    return VideoAnalysisCacheRepository(session)


async def get_comment_analysis_cache_repository(
    session: AsyncSession = Depends(get_db),
) -> CommentAnalysisCacheRepository:
    return CommentAnalysisCacheRepository(session)
