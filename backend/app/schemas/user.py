from typing import Optional
from pydantic import BaseModel, Field

class UserSettingsUpdate(BaseModel):
    """사용자 필터링 설정 업데이트"""
    security_level: Optional[int] = Field(None, description="보안 레벨 (1~5)", ge=1, le=5)
    risk_threshold: Optional[float] = Field(None, description="위험도 임계값 (0.0~1.0)", ge=0.0, le=1.0)
    use_detail_ai_model: Optional[bool] = Field(None, description="2차 정밀 AI 모델 사용 여부")
    enabled_modules: Optional[str] = Field(None, description="활성화 모듈 콤마 구분 (예: 'SEXUAL,PRIVACY' 또는 'ALL')")
    youtube_channel_id: Optional[str] = Field(None, description="YouTube 채널 ID")
    youtube_channel_name: Optional[str] = Field(None, description="YouTube 채널 이름")
    youtube_channel_url: Optional[str] = Field(None, description="YouTube 채널 URL")
    youtube_thumbnail_url: Optional[str] = Field(None, description="YouTube 채널 프로필 이미지 URL")

class UserSettingsResponse(BaseModel):
    """사용자 필터링 설정 조회 응답"""
    user_id: int
    security_level: int
    risk_threshold: float
    use_detail_ai_model: bool
    enabled_modules: str
    youtube_channel_id: Optional[str] = None
    youtube_channel_name: Optional[str] = None
    youtube_channel_url: Optional[str] = None
    youtube_thumbnail_url: Optional[str] = None