from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import UserCreate, UserLogin, Token
from app.repositories.user import UserRepository
from app.api.deps import get_user_repository, get_current_user
from app.core.security import create_access_token
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=Token, summary="회원가입")
async def register(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """새 사용자를 등록하고 JWT 토큰을 발급합니다."""
    
    # 중복 체크
    existing_user = await user_repo.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 사용자명입니다."
        )
    
    # 사용자 생성
    user = await user_repo.create_user_with_password(user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 생성에 실패했습니다."
        )
    
    # 토큰 발급
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id
    }


@router.post("/login", response_model=Token, summary="로그인")
async def login(
    credentials: UserLogin,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """사용자 인증 후 JWT 토큰을 발급합니다."""
    
    user = await user_repo.authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자명 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 토큰 발급
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id
    }

@router.get("/me", summary="현재 사용자 정보 조회")
async def get_me(
    current_user_id: int = Depends(get_current_user)
):
    """JWT 토큰으로 현재 로그인한 사용자 정보 조회"""
    return {
        "user_id": current_user_id,
        "message": "인증 성공!"
    }