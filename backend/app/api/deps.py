import os
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

from app.repositories.user_repository import UserRepository
from app.repositories.dictionary_repository import DictionaryRepository
from app.engines.first_pass_filter import FirstPassFilter
from app.engines.second_pass_filter import SecondPassFilter
from app.engines.risk_scorer import RiskScorer
from app.engines.policy_manager import PolicyManager
from app.services.dictionary_service import DictionaryService
from app.services.comment_filtering_service import CommentFilteringService
from app.clients.youtube_client import YouTubeClient

# --- [Repositories] ---
async def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)

async def get_dictionary_repository(session: AsyncSession = Depends(get_db)) -> DictionaryRepository:
    return DictionaryRepository(session)

# --- [Engines] ---
async def get_first_pass_filter(repo: DictionaryRepository = Depends(get_dictionary_repository)) -> FirstPassFilter:
    return FirstPassFilter(repo=repo)

async def get_second_pass_filter() -> SecondPassFilter:
    return SecondPassFilter()

async def get_risk_scorer() -> RiskScorer:
    return RiskScorer()

async def get_policy_manager() -> PolicyManager:
    return PolicyManager()

# --- [Services] ---
async def get_dictionary_service(repo: DictionaryRepository = Depends(get_dictionary_repository)) -> DictionaryService:
    return DictionaryService(repo=repo)

async def get_comment_filtering_service(
    user_repo: UserRepository = Depends(get_user_repository),
    first_pass: FirstPassFilter = Depends(get_first_pass_filter),
    second_pass: SecondPassFilter = Depends(get_second_pass_filter),
    scorer: RiskScorer = Depends(get_risk_scorer),
    policy: PolicyManager = Depends(get_policy_manager)
) -> CommentFilteringService:
    return CommentFilteringService(user_repo, first_pass, second_pass, scorer, policy)

# --- [Clients] ---
async def get_youtube_client() -> YouTubeClient:
    return YouTubeClient()