from fastapi import Depends, Request

from app.repositories.dictionary import DictionaryRepository
from app.repositories.user import UserRepository
from app.services.filtering.kiwi_engine import KiwiEngine
from app.services.filtering.first_pass_filter import FirstPassFilter
from app.services.filtering.second_pass_filter import SecondPassFilter
from app.services.filtering.risk_scorer import RiskScorer
from app.services.filtering.policy_manager import PolicyManager
from app.services.filtering.service import TextAnalysisService
from app.services.dictionary_service import DictionaryService
from app.services.youtube_analysis_service import YoutubeAnalysisService
from app.services.user_service import UserService
from app.services.auth_service import AuthService

from .repositories import get_dictionary_repository, get_user_repository


# --- Filtering Pipeline (singletons from app.state) ---

def get_kiwi_engine(request: Request) -> KiwiEngine:
    return request.app.state.kiwi_engine


def get_first_pass_filter(request: Request) -> FirstPassFilter:
    return request.app.state.first_pass_filter


def get_second_pass_filter(request: Request) -> SecondPassFilter:
    return request.app.state.second_pass_filter


def get_risk_scorer(request: Request) -> RiskScorer:
    return request.app.state.risk_scorer


def get_policy_manager(request: Request) -> PolicyManager:
    return request.app.state.policy_manager


# --- Application Services ---

async def get_dictionary_service(
    repo: DictionaryRepository = Depends(get_dictionary_repository),
) -> DictionaryService:
    return DictionaryService(repo=repo)


async def get_text_analysis_service(
    first_pass: FirstPassFilter = Depends(get_first_pass_filter),
    second_pass: SecondPassFilter = Depends(get_second_pass_filter),
    scorer: RiskScorer = Depends(get_risk_scorer),
    policy: PolicyManager = Depends(get_policy_manager),
    dict_repo: DictionaryRepository = Depends(get_dictionary_repository),
) -> TextAnalysisService:
    return TextAnalysisService(first_pass, second_pass, scorer, policy, dict_repo)


async def get_youtube_analysis_service() -> YoutubeAnalysisService:
    return YoutubeAnalysisService()


async def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(repo=repo)


async def get_auth_service(
    repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(repo=repo)
