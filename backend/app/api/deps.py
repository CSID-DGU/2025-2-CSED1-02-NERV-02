from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.db.models import User
from app.core.security import decode_access_token

from app.repositories.user import UserRepository
from app.repositories.comment_analysis_cache_repository import CommentAnalysisCacheRepository
from app.repositories.dictionary import DictionaryRepository
from app.repositories.video_analysis_cache_repository import VideoAnalysisCacheRepository
from app.services.filtering.first_pass_filter import FirstPassFilter
from app.services.filtering.second_pass_filter import SecondPassFilter
from app.services.filtering.risk_scorer import RiskScorer
from app.services.filtering.policy_manager import PolicyManager
from app.services.filtering.keyword_extractor import KeywordExtractor
from app.services.filtering.service import TextAnalysisService
from app.services.dictionary_service import DictionaryService
from app.services.youtube_analysis_service import YoutubeAnalysisService
from app.services.user_service import UserService
from app.services.auth_service import AuthService


# --- [Repositories] ---

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
    session: AsyncSession = Depends(get_db)
) -> VideoAnalysisCacheRepository:
    return VideoAnalysisCacheRepository(session)

async def get_comment_analysis_cache_repository(
    session: AsyncSession = Depends(get_db)
) -> CommentAnalysisCacheRepository:
    return CommentAnalysisCacheRepository(session)

# --- [YouTube Clients] ---


# --- [Filtering Pipeline] ---
def get_first_pass_filter(request: Request) -> FirstPassFilter:
    return request.app.state.first_pass_filter

def get_second_pass_filter(request: Request) -> SecondPassFilter:
    return request.app.state.second_pass_filter

def get_risk_scorer(request: Request) -> RiskScorer:
    return request.app.state.risk_scorer

def get_policy_manager(request: Request) -> PolicyManager:
    return request.app.state.policy_manager

def get_keyword_extractor(request: Request) -> KeywordExtractor:
    return request.app.state.keyword_extractor

# --- [Services] ---
async def get_dictionary_service(repo: DictionaryRepository = Depends(get_dictionary_repository)) -> DictionaryService:
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

async def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo=repo)

async def get_auth_service(repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(repo=repo)

# --- [Authentication] ---
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 정보입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: int | None = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 유효하지 않습니다."
        )
    
    user = await user_repo.get_user_settings(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비활성화된 계정입니다."
        )   
    
    return user