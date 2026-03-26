from typing import Optional
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    """회원가입 요청"""
    username: str = Field(..., min_length=3, max_length=50, description="사용자명")
    password: str = Field(..., min_length=6, description="비밀번호 (최소 6자)")

class UserLogin(BaseModel):
    """로그인 요청"""
    username: str = Field(..., description="사용자명")
    password: str = Field(..., description="비밀번호")

class Token(BaseModel):
    """JWT 토큰 응답"""
    access_token: str = Field(..., description="JWT 액세스 토큰")
    token_type: str = Field(default="bearer", description="토큰 타입")
    user_id: int = Field(..., description="사용자 ID")

class TokenData(BaseModel):
    """토큰에서 추출한 데이터"""
    username: Optional[str] = Field(None, description="사용자명")
    user_id: Optional[int] = Field(None, description="사용자 ID")