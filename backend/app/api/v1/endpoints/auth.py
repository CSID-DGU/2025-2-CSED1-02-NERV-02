from fastapi import APIRouter, Depends

from app.db.models import User
from app.schemas import UserCreate, UserLogin, Token
from app.api.deps import get_current_user, get_auth_service
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/register", response_model=Token, summary="회원가입")
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)

):
    """새 사용자를 등록하고 JWT 토큰을 발급합니다."""
    return await auth_service.register(user_data.username, user_data.password)


@router.post("/login", response_model=Token, summary="로그인")
async def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """사용자 인증 후 JWT 토큰을 발급합니다."""
    return await auth_service.login(credentials.username, credentials.password)


@router.get("/me", summary="현재 사용자 정보 조회")
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """JWT 토큰으로 현재 로그인한 사용자 정보 조회"""
    return {
        "user_id": current_user.id,
        "message": "인증 성공!"
    }